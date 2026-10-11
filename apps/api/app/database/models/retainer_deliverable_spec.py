from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import DeliverableType
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.retainer import Retainer


class RetainerDeliverableSpec(Base, TimestampMixin):
    """
    What is owed every month, as a rule rather than as work.

    "4 reels and 2 stories" is two rows. When a period is created,
    these are expanded into individual deliverables - 4 reel rows
    and 2 story rows - so each one can be submitted, revised and
    approved on its own.
    """

    __tablename__ = "retainer_deliverable_specs"

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

    deliverable_type: Mapped[DeliverableType] = mapped_column(
        Enum(DeliverableType, name="deliverable_type"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
    )

    notes: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    retainer: Mapped["Retainer"] = relationship(
        "Retainer",
        back_populates="specs",
    )

    def __repr__(self) -> str:
        return (
            f"<RetainerDeliverableSpec {self.quantity}x"
            f"{self.deliverable_type}>"
        )
