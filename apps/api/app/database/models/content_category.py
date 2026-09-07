from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.creator_profile import CreatorProfile


creator_categories = Table(
    "creator_categories",
    Base.metadata,
    Column(
        "profile_id",
        UUID(as_uuid=True),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("content_categories.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class ContentCategory(Base, TimestampMixin):
    """
    A canonical list rather than free text, so discovery filters
    do not fragment across "Fitness", "fitness" and "Gym".
    """

    __tablename__ = "content_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    profiles: Mapped[list["CreatorProfile"]] = relationship(
        "CreatorProfile",
        secondary=creator_categories,
        back_populates="categories",
    )

    def __repr__(self) -> str:
        return f"<ContentCategory {self.slug}>"
