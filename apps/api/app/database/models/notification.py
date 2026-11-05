from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums.notification import NotificationKind
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User


# After this many failed attempts the row is left alone. A
# provider that has refused five times is not going to accept the
# sixth, and a queue that retries for ever hides the problem
# instead of showing it.
MAX_ATTEMPTS = 5


class Notification(Base, TimestampMixin):
    """
    One email that should be sent, written down before it is.

    An outbox rather than sending inline, for one reason: a
    notification is a consequence of something, never the thing
    itself. Accepting an offer must not fail because a mail
    provider is down, and must not take four seconds because the
    provider is slow. So the accept writes a row in the same
    transaction as the acceptance - either both happened or
    neither did - and something else sends it afterwards.

    What is stored is the *facts*, as JSON, not the rendered
    email. Two reasons. A template fixed after the fact then
    fixes everything still queued, which rendering at write time
    would not. And the facts are frozen at the moment they were
    true, so an email about a retainer still says the right
    amount after somebody edits it - the same reason the retainer
    history keeps actor_name rather than looking it up.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Who it is for. The address is copied in beside them because
    # it is where this was meant to go: somebody changing their
    # email should not silently redirect mail queued before the
    # change.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    to_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    kind: Mapped[NotificationKind] = mapped_column(
        Enum(NotificationKind, name="notification_kind"),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    # Not before this. Used by the message nudge, which waits to
    # see whether the person reads the thread themselves before
    # an email goes out about it.
    send_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # What this is about, so a second event about the same thing
    # can replace a queued one rather than queue beside it. Three
    # messages in a conversation before anybody looks should be
    # one email, not three.
    dedupe_key: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Set when the thing it was about stopped mattering before it
    # went out - the person read the conversation, the request
    # was withdrawn. Kept rather than deleted, because "we chose
    # not to send this" is worth being able to see.
    dropped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    dropped_reason: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Overrides the mixin's, and for the same reason Message
    # overrides it: the drain decides whether a nudge is still
    # worth sending by comparing a read mark against this, and a
    # read mark is written from Python with microseconds. Taking
    # this from the database clock instead - which truncates to
    # the second on SQLite - makes a row queued in the same
    # second as somebody's last read look older than that read,
    # and the email is dropped as already seen.
    #
    # The server_default stays as a floor for anything inserted
    # outside the ORM.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user: Mapped["User"] = relationship()

    @property
    def is_pending(self) -> bool:
        return (
            self.sent_at is None
            and self.dropped_at is None
            and self.attempts < MAX_ATTEMPTS
        )

    def __repr__(self) -> str:
        return f"<Notification {self.kind.value} -> {self.to_email}>"
