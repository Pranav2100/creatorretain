from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database.models.notification import (
    MAX_ATTEMPTS,
    Notification,
)
from app.database.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """
    The outbox, read and written.

    Nothing here decides whether to send anything - that is the
    service's job. This only knows how to put a row in, find the
    ones that are due, and record what happened to them.
    """

    def __init__(self, db: Session):
        super().__init__(db, Notification)

    def add(
        self,
        user_id: UUID,
        to_email: str,
        kind,
        payload: dict,
        send_after: datetime,
        dedupe_key: str | None = None,
    ) -> Notification:
        row = Notification(
            user_id=user_id,
            to_email=to_email,
            kind=kind,
            payload=payload,
            send_after=send_after,
            dedupe_key=dedupe_key,
        )

        self.db.add(row)
        self.db.flush()

        return row

    def pending_with_key(
        self,
        user_id: UUID,
        dedupe_key: str,
    ) -> Notification | None:
        """
        A row already waiting about this same thing.

        What stops three messages in a conversation becoming
        three emails: the second and third find the first still
        queued and leave it alone.
        """
        return (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.dedupe_key == dedupe_key,
                Notification.sent_at.is_(None),
                Notification.dropped_at.is_(None),
            )
            .first()
        )

    def due(
        self,
        now: datetime,
        limit: int = 50,
    ) -> list[Notification]:
        """
        Everything that should go out, oldest first.

        Oldest first so a backlog drains in the order things
        happened - an offer and its acceptance arriving in the
        wrong order would be worse than either arriving late.
        """
        return (
            self.db.query(Notification)
            .options(joinedload(Notification.user))
            .filter(
                Notification.sent_at.is_(None),
                Notification.dropped_at.is_(None),
                Notification.attempts < MAX_ATTEMPTS,
                Notification.send_after <= now,
            )
            .order_by(Notification.send_after.asc())
            .limit(limit)
            .all()
        )

    def mark_sent(self, row: Notification, now: datetime) -> None:
        row.sent_at = now
        row.attempts += 1
        row.last_error = None
        self.db.flush()

    def mark_failed(self, row: Notification, error: str) -> None:
        row.attempts += 1
        # Truncated: a provider that returns a wall of HTML should
        # not put a wall of HTML in the database.
        row.last_error = error[:2000]
        self.db.flush()

    def drop(
        self,
        row: Notification,
        now: datetime,
        reason: str,
    ) -> None:
        row.dropped_at = now
        row.dropped_reason = reason[:120]
        self.db.flush()

    def stats(self) -> dict[str, int]:
        """A count of each state, for looking at when something smells."""
        total = self.db.query(Notification).count()
        sent = (
            self.db.query(Notification)
            .filter(Notification.sent_at.isnot(None))
            .count()
        )
        dropped = (
            self.db.query(Notification)
            .filter(Notification.dropped_at.isnot(None))
            .count()
        )
        stuck = (
            self.db.query(Notification)
            .filter(
                Notification.sent_at.is_(None),
                Notification.dropped_at.is_(None),
                Notification.attempts >= MAX_ATTEMPTS,
            )
            .count()
        )

        return {
            "total": total,
            "sent": sent,
            "dropped": dropped,
            "given_up": stuck,
            "waiting": total - sent - dropped - stuck,
        }

    def for_user(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[Notification]:
        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
