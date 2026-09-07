from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import DeliverableType
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.creator_profile import CreatorProfile


class CreatorRate(Base, TimestampMixin):
    """
    One row per package. "5 reels" is a quantity, not a separate
    packages table.

    Prices are NUMERIC in whole currency units - rupees, not paise -
    so the stored value reads naturally while staying exact. Never
    float: rounding drift in a commission calculation is the kind of
    bug that costs a customer.
    """

    __tablename__ = "creator_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deliverable_type: Mapped[DeliverableType] = mapped_column(
        Enum(DeliverableType, name="deliverable_type"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    notes: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile",
        back_populates="rates",
    )

    def __repr__(self) -> str:
        return (
            f"<CreatorRate {self.quantity}x"
            f"{self.deliverable_type} {self.price}>"
        )
