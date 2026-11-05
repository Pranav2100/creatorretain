from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.common.enums.notification import (
    NotificationCategory,
    NotificationKind,
)
from app.common.permissions import (
    WorkspacePermission,
    permissions_for,
)
from app.database.models.notification import Notification
from app.database.models.retainer import Retainer
from app.database.models.user import User
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
from app.services.email import EmailSender
from app.services.email.templates import build_notification_email


# How long a message sits before an email goes out about it.
#
# Long enough that somebody already in the app reads it first and
# the email is never sent; short enough that somebody who is not
# hears within the quarter hour. The drain checks the read marks
# again before sending, so this is a floor rather than a promise.
MESSAGE_QUIET_PERIOD = timedelta(minutes=10)


# What a retainer event is worth emailing about, if anything.
#
# Deliberately not every RetainerEventKind. A withdrawn offer and
# a withdrawn request belong in the history and in nobody's
# inbox - the person who withdrew it knows, and the other side
# never knew it was there.
FROM_RETAINER_EVENT: dict[str, NotificationKind] = {
    "offered": NotificationKind.OFFER_RECEIVED,
    "accepted": NotificationKind.OFFER_ACCEPTED,
    "declined": NotificationKind.OFFER_DECLINED,
    "pause_requested": NotificationKind.PAUSE_REQUESTED,
    "resume_requested": NotificationKind.RESUME_REQUESTED,
    "request_rejected": NotificationKind.REQUEST_REJECTED,
    "paused": NotificationKind.PAUSED,
    "resumed": NotificationKind.RESUMED,
    "notice_given": NotificationKind.NOTICE_GIVEN,
    "ended": NotificationKind.ENDED,
    "work_submitted": NotificationKind.WORK_SUBMITTED,
    "work_approved": NotificationKind.WORK_APPROVED,
    "changes_requested": NotificationKind.CHANGES_REQUESTED,
    "work_rejected": NotificationKind.WORK_REJECTED,
}


class NotificationService:
    """
    Decides who hears about something, and later sends it.

    Two halves that never run at the same time. Writing is called
    from inside whatever just happened, in that transaction, and
    must be cheap and must not fail - the worst thing it can do
    is take an acceptance down with it. Sending is called by the
    drain, afterwards, where being slow or failing is survivable.
    """

    def __init__(
        self,
        repository: NotificationRepository,
        member_repository: WorkspaceMemberRepository,
        retainer_repository: RetainerRepository,
        custom_role_repository: CustomRoleRepository,
        conversation_repository: ConversationRepository,
        email_sender: EmailSender,
    ):
        self.repository = repository
        self.member_repository = member_repository
        self.retainer_repository = retainer_repository
        self.custom_role_repository = custom_role_repository
        self.conversation_repository = conversation_repository
        self.email_sender = email_sender

    def _now(self) -> datetime:
        return datetime.now(UTC)

    # ------------------------------------------------------------------
    # Who wants to hear about it
    # ------------------------------------------------------------------

    @staticmethod
    def _wants(user: User, kind: NotificationKind) -> bool:
        if kind.is_security:
            return True

        return {
            NotificationCategory.RETAINERS: user.notify_retainers,
            NotificationCategory.MESSAGES: user.notify_messages,
            NotificationCategory.WORK: user.notify_work,
        }.get(kind.category, True)

    def responsible_for(
        self,
        workspace_id: UUID,
        retainer_id: UUID,
    ) -> list[User]:
        """
        The people on this side who should hear about a retainer.

        Whoever the account was put in the hands of, plus whoever
        would have to answer for it if nobody had been - the
        people who can both act on a retainer and see all of
        them, which for the built-in roles means the Owner and
        Admins.

        Not simply everyone who can see it. A Member can read
        every retainer in the workspace and change none of them;
        emailing twenty read-only people about one creator's reel
        is how a team learns to filter the sender.

        Effective permissions, so a custom role carrying
        MANAGE_RETAINERS puts somebody on this list without
        anybody having to remember to update it here.
        """
        members = self.member_repository.get_by_workspace(
            workspace_id,
        )

        assigned = {
            assignment.user_id
            for assignment in self.retainer_repository.assignments_for(
                retainer_id,
            )
        }

        granted = self.custom_role_repository.roles_by_user(
            workspace_id,
        )

        out: list[User] = []

        for member in members:
            if member.user is None:
                continue

            if member.user_id in assigned:
                out.append(member.user)
                continue

            held = set(permissions_for(member.role))

            for role in granted.get(member.user_id, []):
                held |= role.granted

            if {
                WorkspacePermission.MANAGE_RETAINERS,
                WorkspacePermission.VIEW_ALL_RETAINERS,
            } <= held:
                out.append(member.user)

        return out

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def enqueue(
        self,
        user: User,
        kind: NotificationKind,
        payload: dict,
        *,
        delay: timedelta | None = None,
        dedupe_key: str | None = None,
    ) -> Notification | None:
        """
        Put one email in the outbox, if it is wanted.

        Returns None when nothing was queued, which is an
        ordinary outcome rather than a failure: they turned this
        category off, or there is already one waiting about the
        same thing.
        """
        if not self._wants(user, kind):
            return None

        if not user.email:
            return None

        if dedupe_key and self.repository.pending_with_key(
            user.id,
            dedupe_key,
        ):
            return None

        return self.repository.add(
            user_id=user.id,
            # Copied rather than looked up at send time, so
            # changing your address does not redirect mail queued
            # before the change.
            to_email=user.email,
            kind=kind,
            payload=payload,
            send_after=self._now() + (delay or timedelta(0)),
            dedupe_key=dedupe_key,
        )

    def about_retainer(
        self,
        retainer: Retainer,
        event_kind: str,
        *,
        actor_side: str | None,
        actor_user_id: UUID | None = None,
        note: str | None = None,
        subject: str | None = None,
    ) -> list[Notification]:
        """
        Tell the other side that something happened.

        The other side, not both: the person who did it does not
        need an email saying they did it. Where the event has no
        side - something the system did rather than a person -
        both sides hear, because neither of them did it.
        """
        kind = FROM_RETAINER_EVENT.get(event_kind)

        if kind is None:
            return []

        sides: list[tuple[str, UUID]] = [
            ("brand", retainer.brand_workspace_id),
            ("creator", retainer.creator_workspace_id),
        ]

        payload = {
            "retainer_id": str(retainer.id),
            "title": retainer.title,
            "note": note,
            "subject": subject,
            # Frozen here rather than read at send time, for the
            # same reason the history freezes actor_name: an
            # email about what was agreed should still say what
            # was agreed.
            "amount": (
                str(retainer.monthly_amount)
                if retainer.monthly_amount is not None
                else None
            ),
        }

        queued: list[Notification] = []

        for side, workspace_id in sides:
            if actor_side is not None and side == actor_side:
                continue

            for user in self.responsible_for(
                workspace_id,
                retainer.id,
            ):
                if user.id == actor_user_id:
                    continue

                row = self.enqueue(
                    user,
                    kind,
                    payload,
                    # One per person per retainer per kind while
                    # it is still waiting. Approving six
                    # deliverables in a row is one email about
                    # work, not six.
                    dedupe_key=(
                        f"retainer:{retainer.id}:{kind.value}"
                    ),
                )

                if row is not None:
                    queued.append(row)

        return queued

    def about_message(
        self,
        recipient: User,
        conversation_id: UUID,
        *,
        from_name: str,
        is_request: bool,
    ) -> Notification | None:
        """
        Nudge somebody who has not read a conversation.

        Queued behind a quiet period rather than sent, because
        most messages are read by somebody who is already in the
        app and an email about those is noise. The drain looks at
        the read marks again before it sends, so the usual
        outcome is that this row is dropped unsent.
        """
        return self.enqueue(
            recipient,
            (
                NotificationKind.MESSAGE_REQUEST
                if is_request
                else NotificationKind.UNREAD_MESSAGES
            ),
            {
                "conversation_id": str(conversation_id),
                "from_name": from_name,
            },
            delay=MESSAGE_QUIET_PERIOD,
            dedupe_key=f"conversation:{conversation_id}",
        )

    def about_password_change(self, user: User) -> Notification | None:
        return self.enqueue(
            user,
            NotificationKind.PASSWORD_CHANGED,
            {"when": self._now().isoformat()},
        )

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _still_worth_sending(
        self,
        row: Notification,
    ) -> str | None:
        """
        A reason not to send it, or None to go ahead.

        Checked at send time rather than at write time, because
        the whole point of the delay is that the world may have
        moved on - and almost always has, for messages.
        """
        if row.kind not in (
            NotificationKind.UNREAD_MESSAGES,
            NotificationKind.MESSAGE_REQUEST,
        ):
            return None

        raw = (row.payload or {}).get("conversation_id")

        if not raw:
            return None

        mark = self.conversation_repository.read_mark(
            UUID(raw),
            row.user_id,
        )

        if mark is None or mark.read_through is None:
            return None

        read_through = mark.read_through

        if read_through.tzinfo is None:
            read_through = read_through.replace(tzinfo=UTC)

        created = row.created_at

        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)

        if read_through >= created:
            return "they read it before this went out"

        return None

    def drain(self, limit: int = 50) -> dict[str, int]:
        """
        Send what is due. Safe to run again at any time.

        One row at a time, each committed on its own: a provider
        failing on the fourth of fifty must not undo the three
        that went out, and must not send them twice on the next
        run.
        """
        now = self._now()
        rows = self.repository.due(now, limit=limit)

        sent = 0
        failed = 0
        dropped = 0

        for row in rows:
            reason = self._still_worth_sending(row)

            if reason is not None:
                self.repository.drop(row, now, reason)
                self.repository.db.commit()
                dropped += 1
                continue

            try:
                self.email_sender.send(
                    build_notification_email(row),
                )
            except Exception as e:  # noqa: BLE001
                # Deliberately broad. A drain that dies on one
                # bad row stops delivering every row behind it,
                # and the attempt counter is what stops a
                # permanently bad row being retried for ever.
                self.repository.mark_failed(row, repr(e))
                self.repository.db.commit()
                failed += 1
                continue

            self.repository.mark_sent(row, self._now())
            self.repository.db.commit()
            sent += 1

        return {"sent": sent, "failed": failed, "dropped": dropped}
