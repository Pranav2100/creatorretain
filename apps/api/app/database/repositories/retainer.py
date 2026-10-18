from datetime import date
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.common.enums import RetainerStatus
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
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

    def list_for_workspace(
        self,
        workspace_id: UUID,
        statuses: list[RetainerStatus] | None = None,
    ) -> list[Retainer]:
        """
        Both sides of the table in one query. A workspace sees a
        retainer whether it is paying for it or delivering it.
        """
        query = self._loaded().filter(
            or_(
                self.model.brand_workspace_id == workspace_id,
                self.model.creator_workspace_id == workspace_id,
            ),
            self.model.deleted_at.is_(None),
        )

        if statuses:
            query = query.filter(self.model.status.in_(statuses))

        return query.order_by(self.model.created_at.desc()).all()

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
