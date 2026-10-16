from datetime import datetime, timezone
from statistics import median
from uuid import UUID

from app.common.enums import WorkspaceType
from app.common.exceptions import NotFoundError
from app.database.models.workspace import Workspace
from app.database.repositories.brand import BrandRepository
from app.database.repositories.workspace import WorkspaceRepository

# Below this, a review time is an anecdote rather than a habit, and
# publishing it would let one lucky Tuesday stand in for a record.
MIN_REVIEWS = 3


class TrackRecord:
    """Plain carrier; the schema turns it into the response."""

    def __init__(
        self,
        *,
        live_retainers: int,
        creators_worked_with: int,
        member_since: datetime,
        typical_review_hours: float | None,
        reviews_counted: int,
    ):
        self.live_retainers = live_retainers
        self.creators_worked_with = creators_worked_with
        self.member_since = member_since
        self.typical_review_hours = typical_review_hours
        self.reviews_counted = reviews_counted


class BrandService:
    """
    The public view of a workspace that hires.

    Creators are already fully exposed to the other side - bio,
    rates, follower counts, portfolio - while a brand was only ever
    a name on an offer. This is the other half of that trade.
    """

    def __init__(
        self,
        repository: BrandRepository,
        workspace_repository: WorkspaceRepository,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository

    def get_public(self, slug: str) -> Workspace:
        workspace = self.workspace_repository.get_by_slug(slug)

        if workspace is None:
            raise NotFoundError("No such workspace.")

        if workspace.workspace_type == WorkspaceType.CREATOR:
            # Creators have their own page, with rates and a
            # portfolio on it. Sending them through this one would
            # show a creator an empty hiring record.
            raise NotFoundError(
                "That is a creator. Open their creator profile "
                "instead."
            )

        return workspace

    def track_record(self, workspace: Workspace) -> TrackRecord:
        gaps = self.repository.recent_review_gaps(workspace.id)

        hours = [
            self._hours_between(submitted, reviewed)
            for submitted, reviewed in gaps
        ]

        return TrackRecord(
            live_retainers=self.repository.count_live_retainers(
                workspace.id,
            ),
            creators_worked_with=(
                self.repository.count_creators_worked_with(
                    workspace.id,
                )
            ),
            member_since=workspace.created_at,
            typical_review_hours=(
                round(median(hours), 1)
                if len(hours) >= MIN_REVIEWS
                else None
            ),
            reviews_counted=len(hours),
        )

    @staticmethod
    def _hours_between(submitted: datetime, reviewed: datetime) -> float:
        """
        SQLite hands back naive datetimes where PostgreSQL hands
        back aware ones, and subtracting one kind from the other
        raises. Both are stored as UTC, so the fix is to say so.
        """
        if submitted.tzinfo is None:
            submitted = submitted.replace(tzinfo=timezone.utc)

        if reviewed.tzinfo is None:
            reviewed = reviewed.replace(tzinfo=timezone.utc)

        seconds = (reviewed - submitted).total_seconds()

        # Clamped at zero rather than trusted blindly. A resubmission
        # clears reviewed_at so this should never be negative, but a
        # trust number is the wrong place to find that out.
        return max(seconds, 0) / 3600
