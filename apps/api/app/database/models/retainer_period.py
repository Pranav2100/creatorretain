from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import OUTSTANDING_STATUSES
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.retainer import Retainer
    from app.database.models.retainer_deliverable import (
        RetainerDeliverable,
    )


class RetainerPeriod(Base, TimestampMixin):
    """
    One month of a retainer.

    Created from the retainer's rule as time passes, never in
    advance. The amount is copied in rather than read through the
    retainer, so raising the rate in March leaves January's record
    showing what was actually agreed in January.

    There is no stored status. Whether a period is upcoming,
    current or past is a question about today's date, and whether
    it is finished is a question about its deliverables. Storing
    either would mean keeping two sources of truth in step.
    """

    __tablename__ = "retainer_periods"
    __table_args__ = (
        UniqueConstraint(
            "retainer_id",
            "sequence",
            name="uq_retainer_period_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    retainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retainers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequence: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    retainer: Mapped["Retainer"] = relationship(
        "Retainer",
        back_populates="periods",
    )

    deliverables: Mapped[list["RetainerDeliverable"]] = relationship(
        "RetainerDeliverable",
        back_populates="period",
        cascade="all, delete-orphan",
        order_by="RetainerDeliverable.position",
    )

    def state(self, today: date) -> str:
        if today < self.period_start:
            return "upcoming"

        if today > self.period_end:
            return "past"

        return "current"

    @property
    def outstanding_count(self) -> int:
        return sum(
            1
            for item in self.deliverables
            if item.status in OUTSTANDING_STATUSES
        )

    @property
    def is_complete(self) -> bool:
        return self.outstanding_count == 0

    def days_remaining(self, today: date) -> int:
        return (self.period_end - today).days

    def __repr__(self) -> str:
        return (
            f"<RetainerPeriod {self.sequence} "
            f"{self.period_start}..{self.period_end}>"
        )
