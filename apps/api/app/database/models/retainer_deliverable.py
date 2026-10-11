from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import DeliverableStatus, DeliverableType
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.retainer_period import RetainerPeriod
    from app.database.models.user import User


class RetainerDeliverable(Base, TimestampMixin):
    """
    One unit of work. "4 reels" is four of these, not one row with
    a quantity, because a brand approves the first reel and asks
    for changes on the third - which a counter cannot express.
    """

    __tablename__ = "retainer_deliverables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retainer_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deliverable_type: Mapped[DeliverableType] = mapped_column(
        Enum(DeliverableType, name="deliverable_type"),
        nullable=False,
    )

    # Order within the period, so "reel 2 of 4" is stable rather
    # than depending on whatever order rows come back in.
    position: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
    )

    status: Mapped[DeliverableStatus] = mapped_column(
        Enum(DeliverableStatus, name="deliverable_status"),
        nullable=False,
        default=DeliverableStatus.PENDING,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    submitted_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    submitted_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Kept across revisions so "submitted twice, approved on the
    # second go" is visible rather than inferred.
    submission_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    period: Mapped["RetainerPeriod"] = relationship(
        "RetainerPeriod",
        back_populates="deliverables",
    )

    reviewed_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[reviewed_by_user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<RetainerDeliverable {self.deliverable_type.value} "
            f"#{self.position} {self.status.value}>"
        )
