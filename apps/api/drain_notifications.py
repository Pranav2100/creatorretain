"""
Send whatever is waiting in the outbox.

Run it on a schedule. Every minute is fine and so is every five:
nothing here is urgent to the second, and the message nudge
deliberately waits ten minutes anyway.

    uv run python drain_notifications.py
    uv run python drain_notifications.py --limit 200
    uv run python drain_notifications.py --stats

Safe to run twice at once in the sense that nothing is sent
twice - each row is committed as it is sent - but there is no
row locking, so two drains racing could both pick up the same
row and both try it. One scheduled runner is the intended setup.

Exits non-zero if anything failed to send, so a scheduler that
watches exit codes notices a provider that has stopped working.
"""

import argparse
import logging
import sys

# Every model, so SQLAlchemy can resolve the relationships
# between them. Importing only the repositories leaves mappers
# half configured and the first query raises about a name it
# cannot find - the suites import this for the same reason.
import app.database.registry  # noqa: F401
from app.database.repositories.conversation import (
    ConversationRepository,
)
from app.database.repositories.custom_role import (
    CustomRoleRepository,
)
from app.database.repositories.notification import (
    NotificationRepository,
)
from app.database.repositories.retainer import RetainerRepository
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.database.session import SessionLocal
from app.services.email import get_email_sender
from app.services.notification import NotificationService


def build(db) -> NotificationService:
    return NotificationService(
        repository=NotificationRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        retainer_repository=RetainerRepository(db),
        custom_role_repository=CustomRoleRepository(db),
        conversation_repository=ConversationRepository(db),
        email_sender=get_email_sender(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send queued notification emails.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="How many to attempt in one run (default 50).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show the state of the outbox and send nothing.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Say nothing unless something failed.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(message)s",
    )

    db = SessionLocal()

    try:
        service = build(db)

        if args.stats:
            counts = service.repository.stats()
            width = max(len(k) for k in counts)

            for name, value in counts.items():
                print(f"  {name.ljust(width)}  {value}")

            return 0

        result = service.drain(limit=args.limit)

        if not args.quiet or result["failed"]:
            print(
                f"sent {result['sent']}, "
                f"dropped {result['dropped']}, "
                f"failed {result['failed']}"
            )

        # Non-zero so a scheduler notices. Dropping is not a
        # failure - it is the system deciding an email stopped
        # being worth sending, which is working as intended.
        return 1 if result["failed"] else 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
