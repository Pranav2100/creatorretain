from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import SocialPlatform
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.creator_profile import CreatorProfile


class CreatorPortfolioItem(Base, TimestampMixin):
    __tablename__ = "creator_portfolio_items"

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

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    platform: Mapped[SocialPlatform | None] = mapped_column(
        Enum(SocialPlatform, name="social_platform"),
        nullable=True,
    )

    external_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Creators lead with their best work, which is rarely the newest.
    position: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
    )

    profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile",
        back_populates="portfolio_items",
    )

    def __repr__(self) -> str:
        return f"<CreatorPortfolioItem {self.title}>"
