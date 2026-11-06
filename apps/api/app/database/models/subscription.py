from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.subscription import SubscriptionStatus
from app.common.enums.workspace_plan import WorkspacePlan
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.workspace import Workspace


class Subscription(Base, TimestampMixin):
    """
    What a workspace is paying for, and who is collecting it.

    This table is a record of the arrangement with the provider.
    It is **not** where the application reads whether a workspace
    is paid for - that comes from the workspace's own plan and
    plan_expires_at, which this keeps pushed forward as renewals
    arrive.

    Which sounds like duplication and is not. It means a provider
    being unreachable, a webhook arriving late, or this table
    being wrong cannot silently take away something somebody paid
    for: the workspace carries its own paid-until date, and a
    subscription that stops renewing lapses by that date passing
    rather than by anybody noticing. Nothing has to run for the
    right thing to happen.

    The provider's id is kept because that is the only shared
    handle between us and them - webhooks arrive naming it, and
    without it a renewal cannot be matched to a workspace.
    """

    __tablename__ = "subscriptions"

    __table_args__ = (
        # Two rows for one provider subscription would mean a
        # renewal applied twice.
        UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_subscription_provider_ref",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "razorpay", "stripe", "fake". Stored rather than assumed,
    # because a workspace that moves between providers has one
    # row from each and the old id must not be read as the new
    # one's.
    provider: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    provider_subscription_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    # What was bought. Kept here as well as on the workspace
    # because the workspace's plan is the *current* one, and an
    # upgrade mid-cycle changes that before the new subscription
    # has been paid for.
    plan: Mapped[WorkspacePlan] = mapped_column(
        Enum(WorkspacePlan, name="workspace_plan"),
        nullable=False,
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.PENDING,
    )

    # What the provider says this costs, in whole rupees, frozen
    # at the time. A price change should not rewrite what
    # somebody already agreed to.
    amount: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship()

    @property
    def is_live(self) -> bool:
        return self.status.is_live

    def __repr__(self) -> str:
        return (
            f"<Subscription {self.provider}:"
            f"{self.provider_subscription_id} {self.status.value}>"
        )


class BillingEvent(Base, TimestampMixin):
    """
    A webhook we have already dealt with.

    Providers retry. Razorpay will resend an event until it gets
    a 2xx, and a renewal applied twice would push somebody's
    paid-until date a month further than they paid for. So every
    event id is written down the first time and refused the
    second.

    The payload is kept because when a subscription is in a state
    nobody can explain, the sequence of events that produced it
    is the only account of how it got there.
    """

    __tablename__ = "billing_events"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "event_id",
            name="uq_billing_event_ref",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    provider: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    event_id: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        index=True,
    )

    kind: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    provider_subscription_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<BillingEvent {self.provider}:{self.kind}>"
