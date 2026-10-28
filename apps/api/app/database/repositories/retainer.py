from datetime import date
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.common.enums import RetainerStatus
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
from app.database.models.retainer_assignment import (
    RetainerAssignment,
)
from app.database.models.retainer_event import RetainerEvent
from app.database.models.retainer_period import RetainerPeriod
from app.database.repositories.base import BaseRepository


class RetainerRepository(BaseRepository[Retainer]):
    def __init__(self, db: Session):
        super().__init__(db, Retainer)

    def _loaded(self):
        return self.db.query(self.model).options(
            selectinload(self.model.specs),
            selectinload(self.model.periods).selectinload(
                RetainerPeriod.deliverables,
            ),
            joinedload(self.model.brand_workspace),
            joinedload(self.model.creator_workspace),
            # The person who sent the offer, shown to the creator.
            # Loaded here rather than left to lazy loading, which
            # would fire one query per row on a list page.
            joinedload(self.model.created_by),
        )

    def get_full(self, retainer_id: UUID) -> Retainer | None:
        return (
            self._loaded()
            .filter(
                self.model.id == retainer_id,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    def assigned_to(self, user_id: UUID):
        """
        The retainer ids this person has been put on, as something
        another query can test against rather than a list to load.
        """
        return (
            self.db.query(RetainerAssignment.retainer_id)
            .filter(
                RetainerAssignment.user_id == user_id,
                RetainerAssignment.deleted_at.is_(None),
            )
            .subquery()
            .select()
        )

    def list_for_workspace(
        self,
        workspace_id: UUID,
        statuses: list[RetainerStatus] | None = None,
        only_assigned_to: UUID | None = None,
    ) -> list[Retainer]:
        """
        Both sides of the table in one query. A workspace sees a
        retainer whether it is paying for it or delivering it.

        `only_assigned_to` narrows that to the ones a particular
        person has been put on - what a Manager gets. Done in SQL
        rather than by loading everything and filtering after,
        because a list that is filtered in Python is a list that
        was already fetched, and the next person to add a count or
        a page size will get it from the wrong one.
        """
        query = self._loaded().filter(
            or_(
                self.model.brand_workspace_id == workspace_id,
                self.model.creator_workspace_id == workspace_id,
            ),
            self.model.deleted_at.is_(None),
        )

        if only_assigned_to is not None:
            query = query.filter(
                self.model.id.in_(self.assigned_to(only_assigned_to))
            )

        if statuses:
            query = query.filter(self.model.status.in_(statuses))

        return query.order_by(self.model.created_at.desc()).all()

    def record_assignment(
        self,
        assignment: RetainerAssignment,
    ) -> RetainerAssignment:
        """Stages one, to be committed with whatever else changed."""
        self.db.add(assignment)
        return assignment

    def is_assigned(self, retainer_id: UUID, user_id: UUID) -> bool:
        return (
            self.db.query(RetainerAssignment.id)
            .filter(
                RetainerAssignment.retainer_id == retainer_id,
                RetainerAssignment.user_id == user_id,
                RetainerAssignment.deleted_at.is_(None),
            )
            .first()
            is not None
        )

    def assignments_for(
        self,
        retainer_id: UUID,
    ) -> list[RetainerAssignment]:
        return (
            self.db.query(RetainerAssignment)
            .options(joinedload(RetainerAssignment.user))
            .filter(
                RetainerAssignment.retainer_id == retainer_id,
                RetainerAssignment.deleted_at.is_(None),
            )
            .order_by(RetainerAssignment.created_at)
            .all()
        )

    def get_assignment(
        self,
        retainer_id: UUID,
        user_id: UUID,
    ) -> RetainerAssignment | None:
        """
        Including one that was removed, so putting somebody back
        on an account revives the old row rather than colliding
        with it on the way in.
        """
        return (
            self.db.query(RetainerAssignment)
            .filter(
                RetainerAssignment.retainer_id == retainer_id,
                RetainerAssignment.user_id == user_id,
            )
            .first()
        )

    def count_occupying(
        self,
        brand_workspace_id: UUID,
        statuses: tuple[RetainerStatus, ...],
        today: date,
    ) -> int:
        """
        How many of the workspace's plan slots are already taken.

        Counted on the paying side only: being hired does not use
        up a creator's allowance.

        A retainer under notice still counts, because it is still
        running and still being paid for. One whose notice has run
        out does not, even though its stored status never changed:
        the same derivation the model does, written in SQL so the
        count does not have to load every row to work it out.
        """
        return (
            self.db.query(self.model)
            .filter(
                self.model.brand_workspace_id == brand_workspace_id,
                self.model.status.in_(statuses),
                self.model.deleted_at.is_(None),
                or_(
                    self.model.end_date.is_(None),
                    self.model.end_date >= today,
                ),
            )
            .count()
        )

    def find_open_between(
        self,
        brand_workspace_id: UUID,
        creator_workspace_id: UUID,
    ) -> Retainer | None:
        """
        An existing live agreement between these two, so a brand
        cannot stack a second offer on top of an unanswered one.
        """
        return (
            self.db.query(self.model)
            .filter(
                self.model.brand_workspace_id == brand_workspace_id,
                self.model.creator_workspace_id
                == creator_workspace_id,
                self.model.status.in_(
                    (
                        RetainerStatus.PENDING,
                        RetainerStatus.ACTIVE,
                        RetainerStatus.PAUSED,
                    )
                ),
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    # ------------------------------------------------------------------
    # Periods and deliverables
    # ------------------------------------------------------------------

    def existing_sequences(self, retainer_id: UUID) -> set[int]:
        rows = (
            self.db.query(RetainerPeriod.sequence)
            .filter(RetainerPeriod.retainer_id == retainer_id)
            .all()
        )

        return {row[0] for row in rows}

    def list_periods(self, retainer_id: UUID) -> list[RetainerPeriod]:
        return (
            self.db.query(RetainerPeriod)
            .options(selectinload(RetainerPeriod.deliverables))
            .filter(RetainerPeriod.retainer_id == retainer_id)
            .order_by(RetainerPeriod.sequence)
            .all()
        )

    def get_deliverable(
        self,
        deliverable_id: UUID,
    ) -> RetainerDeliverable | None:
        return (
            self.db.query(RetainerDeliverable)
            .options(
                joinedload(RetainerDeliverable.period).joinedload(
                    RetainerPeriod.retainer,
                ),
            )
            .filter(RetainerDeliverable.id == deliverable_id)
            .first()
        )

    def add_period(self, period: RetainerPeriod) -> RetainerPeriod:
        self.db.add(period)
        return period

    def save_deliverable(
        self,
        deliverable: RetainerDeliverable,
    ) -> RetainerDeliverable:
        self.db.add(deliverable)
        self.db.commit()
        self.db.refresh(deliverable)
        return deliverable

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def record(self, event: RetainerEvent) -> RetainerEvent:
        """
        Stages one line of history without committing it.

        Uncommitted on purpose: the event belongs to the change
        that caused it, so both land in the save that follows or
        neither does. A log that can record a pause which did not
        happen is worse than no log.
        """
        self.db.add(event)
        return event

    def events_for(
        self,
        retainer_id: UUID,
        limit: int = 200,
    ) -> list[RetainerEvent]:
        """
        The history, newest first.

        Ordered by time and then by id, because several events can
        share a timestamp - agreeing to a pause writes two in the
        same transaction - and a tie broken differently on each
        read makes a page that reorders itself while you look at
        it.
        """
        return (
            self.db.query(RetainerEvent)
            .options(joinedload(RetainerEvent.actor))
            .filter(RetainerEvent.retainer_id == retainer_id)
            .order_by(
                RetainerEvent.created_at.desc(),
                RetainerEvent.id.desc(),
            )
            .limit(limit)
            .all()
        )
