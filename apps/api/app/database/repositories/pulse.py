from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.common.utils.clock import as_utc
from app.database.models.creator_portfolio_item import (
    CreatorPortfolioItem,
)
from app.database.models.creator_profile import CreatorProfile
from app.database.models.creator_rate import CreatorRate
from app.database.models.creator_social_account import (
    CreatorSocialAccount,
)
from app.database.models.conversation import Conversation
from app.database.models.message import Message
from app.database.models.retainer import Retainer
from app.database.models.retainer_assignment import (
    RetainerAssignment,
)
from app.database.models.retainer_event import RetainerEvent
from app.database.models.retainer_period import RetainerPeriod
from app.database.models.workspace import Workspace
from app.database.models.workspace_invitation import (
    WorkspaceInvitation,
)
from app.database.models.workspace_member import WorkspaceMember

# One reading: the newest change in some set of rows, and how many
# rows there are. Two numbers rather than one because a timestamp
# alone cannot tell a deletion from nothing happening, and a count
# alone cannot tell an edit from nothing happening.
Reading = tuple[datetime | None, int]

EMPTY: Reading = (None, 0)


class PulseRepository:
    """
    "Has anything I am looking at changed?", answered in aggregates.

    Every table in this application carries updated_at, which makes
    this possible without a single extra column: a page says what
    it is showing, and this reads the high-water mark of exactly
    those rows. Nothing is loaded, nothing is serialised, and the
    answer is the same two numbers whether the page shows one
    retainer or forty.

    This is polled by every open tab, so each method here must stay
    an aggregate over an index. Anything that would make it load a
    row belongs somewhere else.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # The primitive
    # ------------------------------------------------------------------

    def _read(self, model, stamp, *where) -> Reading:
        row = (
            self.db.query(func.max(stamp), func.count(model.id))
            .filter(*where)
            .one()
        )

        return row[0], row[1] or 0

    @staticmethod
    def combine(readings: list[Reading]) -> Reading:
        """
        Several readings as one.

        The latest of the timestamps and the sum of the counts. A
        page watching three tables wants one answer, and which
        table moved is not a question it has to ask: it re-renders
        the whole route either way.
        """
        latest: datetime | None = None
        total = 0

        for when, count in readings:
            total += count

            if when is not None and (
                latest is None or as_utc(when) > as_utc(latest)
            ):
                latest = when

        return latest, total

    # ------------------------------------------------------------------
    # What a page might be showing
    # ------------------------------------------------------------------

    def _retainer_ids(
        self,
        workspace_id: UUID,
        one: UUID | None,
        assigned_to: UUID | None = None,
    ):
        visible = self.db.query(Retainer.id).filter(
            or_(
                Retainer.brand_workspace_id == workspace_id,
                Retainer.creator_workspace_id == workspace_id,
            ),
            Retainer.deleted_at.is_(None),
        )

        if one is not None:
            visible = visible.filter(Retainer.id == one)

        # Narrowed the same way the list is. Without this a
        # Manager's page would quietly twitch every time something
        # happened on an account that is none of their business -
        # which is a small leak, but a leak with no upside: the
        # refresh it causes shows them nothing new.
        if assigned_to is not None:
            visible = visible.filter(
                Retainer.id.in_(
                    self.db.query(RetainerAssignment.retainer_id)
                    .filter(
                        RetainerAssignment.user_id == assigned_to,
                        RetainerAssignment.deleted_at.is_(None),
                    )
                    .subquery()
                    .select()
                )
            )

        return visible.subquery().select()

    def retainers(
        self,
        workspace_id: UUID,
        retainer_id: UUID | None = None,
        assigned_to: UUID | None = None,
    ) -> Reading:
        """
        Agreements this workspace is party to, on either side.

        The events are read as well as the retainers themselves,
        because that is where most of the news is: a request, an
        answer, a piece of work submitted. Periods are in here too
        for the one case nobody clicks - a new month beginning
        under a page that has been open since yesterday.
        """
        ids = self._retainer_ids(workspace_id, retainer_id, assigned_to)

        return self.combine(
            [
                self._read(
                    Retainer,
                    Retainer.updated_at,
                    Retainer.id.in_(ids),
                ),
                self._read(
                    RetainerEvent,
                    RetainerEvent.created_at,
                    RetainerEvent.retainer_id.in_(ids),
                ),
                self._read(
                    RetainerPeriod,
                    RetainerPeriod.updated_at,
                    RetainerPeriod.retainer_id.in_(ids),
                ),
            ]
        )

    def messages(
        self,
        workspace_id: UUID,
        assigned_to: UUID | None = None,
    ) -> Reading:
        """
        Threads this workspace is part of, and what was said in
        them.

        Narrowed the same way the inbox is, so a manager is not
        told that something arrived in a conversation they cannot
        open.
        """
        mine = self.db.query(Conversation.id).filter(
            or_(
                Conversation.lower_workspace_id == workspace_id,
                Conversation.higher_workspace_id == workspace_id,
            ),
            Conversation.deleted_at.is_(None),
        )

        if assigned_to is not None:
            reachable = (
                self.db.query(Retainer.creator_workspace_id)
                .join(
                    RetainerAssignment,
                    RetainerAssignment.retainer_id == Retainer.id,
                )
                .filter(
                    RetainerAssignment.user_id == assigned_to,
                    RetainerAssignment.deleted_at.is_(None),
                )
                .subquery()
                .select()
            )

            mine = mine.filter(
                or_(
                    Conversation.started_by_user_id == assigned_to,
                    Conversation.lower_workspace_id.in_(reachable),
                    Conversation.higher_workspace_id.in_(reachable),
                )
            )

        ids = mine.subquery().select()

        return self.combine(
            [
                self._read(
                    Conversation,
                    Conversation.updated_at,
                    Conversation.id.in_(ids),
                ),
                self._read(
                    Message,
                    Message.created_at,
                    Message.conversation_id.in_(ids),
                ),
            ]
        )

    def workspace(self, workspace_id: UUID) -> Reading:
        """
        The workspace itself, who is in it, and who has been asked.

        What settings and the team page are made of. An invitation
        accepted in another browser should show up here without
        anyone reloading to find out.
        """
        return self.combine(
            [
                self._read(
                    Workspace,
                    Workspace.updated_at,
                    Workspace.id == workspace_id,
                ),
                self._read(
                    WorkspaceMember,
                    WorkspaceMember.updated_at,
                    WorkspaceMember.workspace_id == workspace_id,
                ),
                self._read(
                    WorkspaceInvitation,
                    WorkspaceInvitation.updated_at,
                    WorkspaceInvitation.workspace_id == workspace_id,
                ),
            ]
        )

    def _profile_ids(self, workspace_id: UUID):
        return (
            self.db.query(CreatorProfile.id)
            .filter(CreatorProfile.workspace_id == workspace_id)
            .subquery()
            .select()
        )

    def profile(self, workspace_id: UUID) -> Reading:
        """A creator's own profile, and everything hanging off it."""
        ids = self._profile_ids(workspace_id)

        return self.combine(
            [
                self._read(
                    CreatorProfile,
                    CreatorProfile.updated_at,
                    CreatorProfile.workspace_id == workspace_id,
                ),
                self._read(
                    CreatorSocialAccount,
                    CreatorSocialAccount.updated_at,
                    CreatorSocialAccount.profile_id.in_(ids),
                ),
                self._read(
                    CreatorRate,
                    CreatorRate.updated_at,
                    CreatorRate.profile_id.in_(ids),
                ),
                self._read(
                    CreatorPortfolioItem,
                    CreatorPortfolioItem.updated_at,
                    CreatorPortfolioItem.profile_id.in_(ids),
                ),
            ]
        )

    def creator(self, creator_workspace_id: UUID) -> Reading:
        """One creator as someone else sees them."""
        return self.profile(creator_workspace_id)

    def discovery(self) -> Reading:
        """
        Every creator who could appear in a search.

        Read across the whole table rather than the result of one
        query, because the page's filters live in the browser's
        URL and reproducing them here would be a second copy of
        the search to keep in step with the first.
        """
        return self._read(
            CreatorProfile,
            CreatorProfile.updated_at,
            CreatorProfile.deleted_at.is_(None),
        )
