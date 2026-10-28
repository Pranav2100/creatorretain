from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.permissions import WorkspacePermission
from app.database.models.conversation import Conversation
from app.database.models.conversation_read import ConversationRead
from app.database.models.message import (
    MAX_MESSAGE_LENGTH,
    Message,
)
from app.database.models.workspace_block import WorkspaceBlock
from app.database.repositories.conversation import (
    ConversationRepository,
)
from app.database.repositories.workspace import WorkspaceRepository
from app.services.workspace_member import (
    WorkspaceContext,
    WorkspaceMemberService,
)

# Anyone may write to anyone, which is a decision with a cost:
# somebody has to be able to open a conversation with a stranger,
# and nobody should be able to open four hundred of them.
#
# Two limits, both about first contact rather than about talking.
# Once the other side has answered, neither applies - two people
# in a conversation are not a problem to be rationed.

#: New conversations one workspace may start in a day.
NEW_CONVERSATIONS_A_DAY = 20

#: Messages you may send to someone who has never replied.
UNANSWERED_LIMIT = 3


class ConversationService:
    """
    Threads between two workspaces.

    Three rules decide everything here, and they are worth
    stating together because they interact:

    One, a conversation belongs to two workspaces, and inside
    each of them it is visible to the seniors, to whoever runs
    that account, and to whoever opened it.

    Two, either side may block the other, and a block stops the
    thread in both directions.

    Three, first contact is rationed and conversation is not.
    """

    def __init__(
        self,
        repository: ConversationRepository,
        workspace_repository: WorkspaceRepository,
        member_service: WorkspaceMemberService,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.member_service = member_service

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def inbox(
        self,
        current_user_id: UUID,
        requests: bool = False,
    ) -> tuple[list[Conversation], dict[UUID, int], UUID]:
        context = self.member_service.resolve_context(current_user_id)

        conversations = self.repository.list_for(
            context.workspace_id,
            self._narrowed_to(context, current_user_id),
            requests=requests,
        )

        unread = self.repository.unread_counts(
            [c.id for c in conversations],
            current_user_id,
            context.workspace_id,
        )

        return conversations, unread, context.workspace_id

    def waiting(self, current_user_id: UUID) -> int:
        """How many strangers are waiting to be let in."""
        context = self.member_service.resolve_context(current_user_id)

        return self.repository.count_requests(
            context.workspace_id,
            self._narrowed_to(context, current_user_id),
        )

    def badge(self, current_user_id: UUID) -> tuple[int, int]:
        """
        What the header needs and nothing else.

        Two numbers, so every signed-in page can carry an honest
        count without fetching a list it is not going to show.
        """
        context = self.member_service.resolve_context(current_user_id)
        narrowed = self._narrowed_to(context, current_user_id)

        conversations = self.repository.list_for(
            context.workspace_id,
            narrowed,
        )

        unread = self.repository.unread_counts(
            [c.id for c in conversations],
            current_user_id,
            context.workspace_id,
        )

        return (
            sum(unread.values()),
            self.repository.count_requests(
                context.workspace_id,
                narrowed,
            ),
        )

    def thread(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> tuple[Conversation, list[Message], UUID]:
        context, conversation = self._reach(
            current_user_id,
            conversation_id,
        )

        messages = self.repository.messages(conversation.id)

        return conversation, messages, context.workspace_id

    def mark_read(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> None:
        """
        Moves this person's mark to now.

        Now rather than the last message's time, because a thread
        read at this moment has been read to the end of itself,
        and borrowing a message's timestamp leaves anything that
        arrives in the same second looking unread forever.
        """
        self._reach(current_user_id, conversation_id)

        mark = self.repository.read_mark(
            conversation_id,
            current_user_id,
        )

        if mark is None:
            mark = ConversationRead(
                conversation_id=conversation_id,
                user_id=current_user_id,
                read_through=self._now(),
            )
            self.repository.add(mark)
        else:
            mark.read_through = self._now()

        self.repository.commit()

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def send(
        self,
        current_user_id: UUID,
        *,
        to_workspace_id: UUID | None = None,
        conversation_id: UUID | None = None,
        body: str,
    ) -> tuple[Conversation, Message]:
        """
        Says something, opening the thread if there is not one.

        Addressed either by conversation or by who it is to, so
        the first message from a creator's page and the hundredth
        from the thread are the same operation. Which matters:
        the limits and the block check have to apply to both, and
        two entry points would mean two places to forget them.
        """
        context = self.member_service.resolve_context(current_user_id)

        said = (body or "").strip()

        if not said:
            raise ConflictError("Write something first.")

        if len(said) > MAX_MESSAGE_LENGTH:
            raise ConflictError(
                f"Messages can be up to {MAX_MESSAGE_LENGTH} "
                "characters."
            )

        if conversation_id is not None:
            _, conversation = self._reach(
                current_user_id,
                conversation_id,
            )
            other = conversation.other_than(context.workspace_id)
        else:
            if to_workspace_id is None:
                raise ConflictError("Say who this is for.")

            other = to_workspace_id
            conversation = self._open(context, current_user_id, other)

        self._refuse_if_blocked(context.workspace_id, other)

        if conversation.declined_at is not None:
            if (
                conversation.started_by_workspace_id
                == context.workspace_id
            ):
                # Said the same way as a block, and for the same
                # reason: "they turned you away" is information
                # the person who turned them away did not offer.
                raise PermissionDeniedError(
                    "This message could not be delivered."
                )

            # The side that turned it away, changing their mind.
            # Writing back is as clear a reversal as there is, and
            # the thread is still here precisely so that this does
            # not mean starting from nothing.
            conversation.declined_at = None

        self._refuse_if_shouting(conversation, context, other)

        # Answering somebody is how you let them in. Doing it here
        # rather than asking the page to call accept first means a
        # reply can never leave a thread half accepted.
        if (
            conversation.accepted_at is None
            and conversation.started_by_workspace_id
            != context.workspace_id
        ):
            conversation.accepted_at = self._now()

        message = Message(
            conversation_id=conversation.id,
            sender_workspace_id=context.workspace_id,
            sender_user_id=current_user_id,
            sender_name=context.workspace.display_name,
            body=said,
        )

        self.repository.add_message(message)

        conversation.last_message_at = self._now()
        conversation.message_count += 1

        self.repository.save(conversation)

        # Sending is reading: nobody should return to a thread
        # they just wrote in and find their own message unread.
        self._touch_read_mark(conversation.id, current_user_id)

        return conversation, message

    def _open(
        self,
        context: WorkspaceContext,
        current_user_id: UUID,
        other: UUID,
    ) -> Conversation:
        if other == context.workspace_id:
            raise ConflictError(
                "You cannot start a conversation with yourself."
            )

        target = self.workspace_repository.get(other)

        if target is None:
            raise NotFoundError("That workspace does not exist.")

        existing = self.repository.between(context.workspace_id, other)

        if existing is not None:
            return existing

        self._refuse_if_blocked(context.workspace_id, other)
        self._refuse_if_too_many_new(context.workspace_id)

        lower, higher = Conversation.order_pair(
            context.workspace_id,
            other,
        )

        conversation = Conversation(
            lower_workspace_id=lower,
            higher_workspace_id=higher,
            started_by_workspace_id=context.workspace_id,
            started_by_user_id=current_user_id,
        )

        return self.repository.create(conversation)

    # ------------------------------------------------------------------
    # Letting somebody in, or not
    # ------------------------------------------------------------------

    def accept(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> Conversation:
        """
        Lets a request into the inbox without answering it yet.

        Worth having alongside replying, because the two are
        different intentions: "I will deal with this" is not the
        same as "here is my answer", and a person should be able
        to clear their requests without being made to write
        something.
        """
        context, conversation = self._reach(
            current_user_id,
            conversation_id,
        )

        if not conversation.is_request_for(context.workspace_id):
            raise ConflictError(
                "That is not waiting on you."
            )

        conversation.accepted_at = self._now()

        return self.repository.save(conversation)

    def decline(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> None:
        """
        Turns a request away.

        The thread leaves the recipient's requests and the sender
        can add nothing more, but the row survives: deleting it
        would let the same stranger start again from nothing, and
        would throw away what was said if the recipient changes
        their mind.
        """
        context, conversation = self._reach(
            current_user_id,
            conversation_id,
        )

        if not conversation.is_request_for(context.workspace_id):
            raise ConflictError(
                "That is not waiting on you."
            )

        conversation.declined_at = self._now()

        self.repository.save(conversation)

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------

    def block(
        self,
        current_user_id: UUID,
        other_workspace_id: UUID,
        reason: str | None = None,
    ) -> WorkspaceBlock:
        context = self.member_service.resolve_context(current_user_id)
        context.require(
            WorkspacePermission.EDIT_WORKSPACE,
            "Only the workspace owner and admins can block "
            "somebody.",
        )

        if other_workspace_id == context.workspace_id:
            raise ConflictError("You cannot block yourself.")

        existing = self.repository.block_by(
            context.workspace_id,
            other_workspace_id,
        )

        if existing is not None:
            existing.deleted_at = None
            existing.reason = reason
            existing.blocked_by_user_id = current_user_id

            return self.repository.save(existing)

        block = WorkspaceBlock(
            blocker_workspace_id=context.workspace_id,
            blocked_workspace_id=other_workspace_id,
            blocked_by_user_id=current_user_id,
            reason=reason,
        )

        self.repository.add_block(block)
        self.repository.commit()

        return block

    def unblock(
        self,
        current_user_id: UUID,
        other_workspace_id: UUID,
    ) -> None:
        context = self.member_service.resolve_context(current_user_id)
        context.require(
            WorkspacePermission.EDIT_WORKSPACE,
            "Only the workspace owner and admins can undo a block.",
        )

        existing = self.repository.block_by(
            context.workspace_id,
            other_workspace_id,
        )

        if existing is None or existing.deleted_at is not None:
            raise NotFoundError("They are not blocked.")

        existing.deleted_at = self._now()
        self.repository.save(existing)

    def blocked(
        self,
        current_user_id: UUID,
    ) -> list[WorkspaceBlock]:
        context = self.member_service.resolve_context(current_user_id)
        context.require(WorkspacePermission.VIEW_MEMBERS)

        return self.repository.blocks_by(context.workspace_id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _reach(
        self,
        current_user_id: UUID,
        conversation_id: UUID,
    ) -> tuple[WorkspaceContext, Conversation]:
        context = self.member_service.resolve_context(current_user_id)

        conversation = self.repository.visible_to(
            conversation_id,
            context.workspace_id,
            self._narrowed_to(context, current_user_id),
        )

        if conversation is None:
            # Not found rather than forbidden, as everywhere else:
            # refusing by name confirms the thing is there.
            raise NotFoundError("Conversation not found.")

        return context, conversation

    @staticmethod
    def _narrowed_to(
        context: WorkspaceContext,
        current_user_id: UUID,
    ) -> UUID | None:
        """
        Whose conversations to filter by, or None for all of them.

        Keyed off the same permission that decides whether
        somebody sees every retainer, so the two cannot drift
        apart and leave a manager reading threads about accounts
        they were taken off.
        """
        if context.allows(WorkspacePermission.VIEW_ALL_RETAINERS):
            return None

        return current_user_id

    def _refuse_if_blocked(self, mine: UUID, other: UUID) -> None:
        if self.repository.block_between(mine, other) is None:
            return

        # Said the same way whichever side blocked. Telling
        # somebody they have been blocked turns a quiet exit into
        # an argument, and the blocked party learning nothing is
        # the point.
        raise PermissionDeniedError(
            "This message could not be delivered."
        )

    def _refuse_if_too_many_new(self, workspace_id: UUID) -> None:
        since = self._now() - timedelta(days=1)

        started = self.repository.started_recently(
            workspace_id,
            since,
        )

        if started >= NEW_CONVERSATIONS_A_DAY:
            raise ConflictError(
                f"You can start {NEW_CONVERSATIONS_A_DAY} new "
                "conversations a day. Try again tomorrow."
            )

    def _refuse_if_shouting(
        self,
        conversation: Conversation,
        context: WorkspaceContext,
        other: UUID,
    ) -> None:
        """
        Stops somebody filling a stranger's requests on their own.

        Tied to acceptance rather than to a reply, because those
        come apart: somebody can accept a request and say nothing
        for a week, and rationing them for that week would be
        rationing a conversation they have already agreed to.
        """
        if conversation.accepted_at is not None:
            return

        if conversation.started_by_workspace_id != context.workspace_id:
            # Answering a request is how you accept it, so the
            # side being written to is never the one shouting.
            return

        mine = self.repository.sent_since(
            conversation.id,
            context.workspace_id,
        )

        if mine >= UNANSWERED_LIMIT:
            raise ConflictError(
                "They have not accepted your messages yet. Wait "
                "for an answer before sending more."
            )

    def _touch_read_mark(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> None:
        mark = self.repository.read_mark(conversation_id, user_id)

        if mark is None:
            self.repository.add(
                ConversationRead(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    read_through=self._now(),
                )
            )
        else:
            mark.read_through = self._now()

        self.repository.commit()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
