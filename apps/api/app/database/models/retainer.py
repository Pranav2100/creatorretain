from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    TERMINAL_STATUSES,
    RetainerRequest,
    RetainerStatus,
)
from app.common.utils.billing_periods import anchor_day
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.retainer_deliverable_spec import (
        RetainerDeliverableSpec,
    )
    from app.database.models.retainer_period import RetainerPeriod
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


class Retainer(Base, TimestampMixin):
    """
    A standing agreement between a hiring workspace and a creator.

    This row is the RULE, not the work. It says "40,000 a month for
    4 reels, starting 12 October" once. The months themselves live
    in retainer_periods and are created from this rule as time
    passes, so changing the rate next year does not rewrite last
    year's history.
    """

    __tablename__ = "retainers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # The workspace paying. A brand, or an agency hiring on behalf
    # of one - both sit on the same side of the table.
    brand_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    creator_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    status: Mapped[RetainerStatus] = mapped_column(
        Enum(RetainerStatus, name="retainer_status"),
        nullable=False,
        default=RetainerStatus.PENDING,
        index=True,
    )

    # Whole rupees, never float. A commission calculated off a
    # float drifts, and drift in money is the bug that loses a
    # customer rather than annoying them.
    monthly_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # Null means open-ended, which is the normal case. A retainer
    # ends when someone ends it, not on a date set at signing.
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    notice_period_days: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=30,
    )

    # Pausing moves the start date to the day work resumes, which
    # would otherwise make the next period number 1 again and
    # collide with the first one. The offset carries the count
    # across the gap, so periods stay 1, 2, 3, 4 either side of it.
    sequence_offset: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
    )

    terms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # A change one side has asked for, waiting on the other
    # ------------------------------------------------------------------
    # Only one at a time: there is no sensible reading of "pause
    # this" and "resume this" both outstanding.
    pending_action: Mapped[RetainerRequest | None] = mapped_column(
        Enum(RetainerRequest, name="retainer_request"),
        nullable=True,
    )

    # The side that asked, not the person. A request should still
    # be answerable after whoever typed it leaves the workspace.
    pending_by_side: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    pending_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    pending_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    pending_reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    # When notice was served, and by whom. Separate from ended_at,
    # which is the day it actually finishes.
    notice_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notice_given_by_side: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    brand_workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[brand_workspace_id],
    )

    creator_workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[creator_workspace_id],
    )

    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    specs: Mapped[list["RetainerDeliverableSpec"]] = relationship(
        "RetainerDeliverableSpec",
        back_populates="retainer",
        cascade="all, delete-orphan",
    )

    periods: Mapped[list["RetainerPeriod"]] = relationship(
        "RetainerPeriod",
        back_populates="retainer",
        cascade="all, delete-orphan",
        order_by="RetainerPeriod.sequence",
    )

    @property
    def anchor_day(self) -> int:
        """The day of the month each new period begins on."""
        return anchor_day(self.start_date)

    def state(self, today: date) -> RetainerStatus:
        """
        What this retainer actually is on a given day.

        Ending serves notice rather than stopping dead, so between
        the day notice is given and the day it runs out the stored
        status is still ACTIVE - the work continues and so does
        the money. Past that date it reads as ENDED without
        anything having had to run, the same way a lapsed plan
        reads as Free.

        Takes the day as an argument rather than asking the clock,
        so a caller testing next February gets next February's
        answer.
        """
        if self.status in TERMINAL_STATUSES:
            return self.status

        if self.end_date is not None and today > self.end_date:
            return RetainerStatus.ENDED

        return self.status

    def is_under_notice(self, today: date) -> bool:
        """Notice served, but not yet run out."""
        return (
            self.notice_given_at is not None
            and self.end_date is not None
            and today <= self.end_date
            and self.status not in TERMINAL_STATUSES
        )

    @property
    def is_running(self) -> bool:
        """Whether time should still be producing new periods."""
        return self.status == RetainerStatus.ACTIVE

    @property
    def monthly_deliverable_count(self) -> int:
        return sum(spec.quantity for spec in self.specs)

    def __repr__(self) -> str:
        return (
            f"<Retainer {self.title} {self.status.value} "
            f"{self.monthly_amount}>"
        )
