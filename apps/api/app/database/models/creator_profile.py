from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    CreatorAvailability,
    CreatorProfileStatus,
    CreatorVerificationStatus,
)
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.content_category import ContentCategory
    from app.database.models.creator_portfolio_item import (
        CreatorPortfolioItem,
    )
    from app.database.models.creator_rate import CreatorRate
    from app.database.models.creator_social_account import (
        CreatorSocialAccount,
    )
    from app.database.models.workspace import Workspace

# JSONB on PostgreSQL, plain JSON elsewhere. Lists rather than a
# native array so the same models run against SQLite in tests.
JSON_LIST = JSON().with_variant(JSONB, "postgresql")


class CreatorProfile(Base, TimestampMixin):
    __tablename__ = "creator_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    headline: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        index=True,
    )

    languages: Mapped[list[str]] = mapped_column(
        JSON_LIST,
        nullable=False,
        default=list,
    )

    skills: Mapped[list[str]] = mapped_column(
        JSON_LIST,
        nullable=False,
        default=list,
    )

    monthly_retainer_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    availability: Mapped[CreatorAvailability] = mapped_column(
        Enum(CreatorAvailability, name="creator_availability"),
        nullable=False,
        default=CreatorAvailability.AVAILABLE,
    )

    verification_status: Mapped[CreatorVerificationStatus] = (
        mapped_column(
            Enum(
                CreatorVerificationStatus,
                name="creator_verification_status",
            ),
            nullable=False,
            default=CreatorVerificationStatus.UNVERIFIED,
        )
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[CreatorProfileStatus] = mapped_column(
        Enum(CreatorProfileStatus, name="creator_profile_status"),
        nullable=False,
        default=CreatorProfileStatus.DRAFT,
        index=True,
    )

    # The creator's own switch. The system decides whether a profile
    # is ready; the creator decides whether it is visible.
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    completeness: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        index=True,
    )

    boosted_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
    )

    social_accounts: Mapped[list["CreatorSocialAccount"]] = (
        relationship(
            "CreatorSocialAccount",
            back_populates="profile",
            cascade="all, delete-orphan",
        )
    )

    portfolio_items: Mapped[list["CreatorPortfolioItem"]] = (
        relationship(
            "CreatorPortfolioItem",
            back_populates="profile",
            cascade="all, delete-orphan",
            order_by="CreatorPortfolioItem.position",
        )
    )

    rates: Mapped[list["CreatorRate"]] = relationship(
        "CreatorRate",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    categories: Mapped[list["ContentCategory"]] = relationship(
        "ContentCategory",
        secondary="creator_categories",
        back_populates="profiles",
    )

    @property
    def is_boosted(self) -> bool:
        if self.boosted_until is None:
            return False

        return self.boosted_until > datetime.now(
            self.boosted_until.tzinfo,
        )

    @property
    def is_discoverable(self) -> bool:
        return (
            self.status == CreatorProfileStatus.PUBLISHED
            and not self.is_hidden
            and self.deleted_at is None
        )

    def __repr__(self) -> str:
        return f"<CreatorProfile {self.workspace_id}>"
