from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import SocialPlatform
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.creator_profile import CreatorProfile


class CreatorSocialAccount(Base, TimestampMixin):
    """
    One platform account per creator.

    Claimed and verified figures are kept side by side rather than
    one overwriting the other. The gap between what a creator says
    and what the platform reports is the most useful thing a brand
    can see before committing to a multi-month retainer.
    """

    __tablename__ = "creator_social_accounts"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "platform",
            name="uq_social_account_profile_platform",
        ),
    )

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

    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform"),
        nullable=False,
        index=True,
    )

    handle: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    profile_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    claimed_followers: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    claimed_engagement_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Filled by platform sync once Verified is purchased. Null today.
    verified_followers: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    verified_engagement_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    profile: Mapped["CreatorProfile"] = relationship(
        "CreatorProfile",
        back_populates="social_accounts",
    )

    @property
    def followers(self) -> int | None:
        """Verified figure when it exists, otherwise the claim."""
        if self.verified_followers is not None:
            return self.verified_followers

        return self.claimed_followers

    @property
    def engagement_rate(self) -> Decimal | None:
        if self.verified_engagement_rate is not None:
            return self.verified_engagement_rate

        return self.claimed_engagement_rate

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None

    def __repr__(self) -> str:
        return f"<CreatorSocialAccount {self.platform} {self.handle}>"
