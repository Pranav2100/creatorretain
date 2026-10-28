from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.user import UserStatus
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # What this person does where they work - "Talent Manager".
    # Nullable because someone running their own creator workspace
    # has no job title and should not be asked to invent one; it
    # is required only to accept an invitation into somebody
    # else's workspace, where a creator on the other side of an
    # offer needs to know who they are dealing with.
    job_title: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Bumped whenever every existing session should stop working -
    # today that means a password change. Each token carries the
    # number it was minted with, and one that does not match is
    # refused.
    #
    # A counter rather than a "password changed at" timestamp on
    # purpose: comparing times means deciding what to do about a
    # token issued in the same second as the change, and there is
    # no answer to that which is both simple and right. Two
    # integers are either equal or they are not.
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.PENDING,
        nullable=False,
    )

    owned_workspaces = relationship(
        "Workspace",
        back_populates="owner",
        cascade="all, delete-orphan",
    )