from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.common.utils.clock import as_utc
from app.database.models.conversation import Conversation
from app.database.models.conversation_read import ConversationRead
from app.database.models.message import Message
from app.database.models.retainer import Retainer
from app.database.models.retainer_assignment import (
    RetainerAssignment,
)
from app.database.models.workspace_block import WorkspaceBlock
from app.database.models.workspace_member import WorkspaceMember
from app.database.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(db, Conversation)

    def _loaded(self):
        return self.db.query(self.model).options(
            joinedload(self.model.lower_workspace),
            joinedload(self.model.higher_workspace),
        )

    # ------------------------------------------------------------------
    # Finding one
    # ------------------------------------------------------------------

    def between(
        self,
        one: UUID,
        other: UUID,
    ) -> Conversation | None:
        lower, higher = Conversation.order_pair(one, other)

        return (
            self._loaded()
            .filter(
                self.model.lower_workspace_id == lower,
                self.model.higher_workspace_id == higher,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    def get_full(self, conversation_id: UUID) -> Conversation | None:
        return (
            self._loaded()
            .filter(
                self.model.id == conversation_id,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    # ------------------------------------------------------------------
    # Who may see which
    # ------------------------------------------------------------------

    def _reachable_creators(self, user_id: UUID):
        """
        The workspaces at the other end of a retainer this person
        has been put on.

        A manager assigned to Nina's account can see the thread
        with Nina. It is the assignment that grants it, not the
        retainer's existence, which is why this goes through the
        assignment table rather than the retainer's workspace
        columns alone.
        """
        return (
            self.db.query(Retainer.creator_workspace_id)
            .join(
                RetainerAssignment,
                RetainerAssignment.retainer_id == Retainer.id,
            )
            .filter(
                RetainerAssignment.user_id == user_id,
                RetainerAssignment.deleted_at.is_(None),
                Retainer.deleted_at.is_(None),
            )
            .subquery()
            .select()
        )

    def _visible(self, workspace_id: UUID, user_id: UUID | None):
        """
        The conversations this workspace has, narrowed to what
        this person may see.

        `user_id` None means no narrowing - what an Owner or an
        Admin gets. Otherwise it is the accounts they run, plus
        anything they started themselves, which is the only way
        somebody can open a thread with a creator nobody has
        hired yet and still find it tomorrow.
        """
        query = self._loaded().filter(
            or_(
                self.model.lower_workspace_id == workspace_id,
                self.model.higher_workspace_id == workspace_id,
            ),
            self.model.deleted_at.is_(None),
        )

        if user_id is None:
            return query

        reachable = self._reachable_creators(user_id)

        return query.filter(
            or_(
                self.model.started_by_user_id == user_id,
                self.model.lower_workspace_id.in_(reachable),
                self.model.higher_workspace_id.in_(reachable),
            )
        )

    def list_for(
        self,
        workspace_id: UUID,
        user_id: UUID | None,
        requests: bool = False,
    ) -> list[Conversation]:
        """
        Newest activity first, which is how an inbox is read.

        `requests` picks the other pile: threads a stranger has
        started and this side has not yet let in. The two are
        separate queries rather than one list filtered after,
        because the unread count on an inbox should not include
        people you have not agreed to hear from - that is the
        whole point of keeping them apart.
        """
        query = self._visible(workspace_id, user_id).filter(
            self.model.declined_at.is_(None)
        )

        if requests:
            query = query.filter(
                self.model.accepted_at.is_(None),
                self.model.started_by_workspace_id != workspace_id,
            )
        else:
            query = query.filter(
                or_(
                    self.model.accepted_at.isnot(None),
                    self.model.started_by_workspace_id
                    == workspace_id,
                )
            )

        return (
            query.order_by(
                self.model.last_message_at.desc().nullslast(),
                self.model.created_at.desc(),
            )
            .all()
        )

    def visible_to(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
        user_id: UUID | None,
    ) -> Conversation | None:
        """
        One conversation, through the same filter as the list.

        Separate from get_full on purpose: a list that is
        filtered beside a read that is not is a filter that does
        nothing, because ids travel.
        """
        return (
            self._visible(workspace_id, user_id)
            .filter(self.model.id == conversation_id)
            .first()
        )

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def messages(
        self,
        conversation_id: UUID,
        limit: int = 200,
    ) -> list[Message]:
        """
        The most recent stretch, oldest first.

        Read backwards and then turned round, so a long thread
        gives you the end of it rather than the beginning - which
        is the part anybody opening a conversation wants.
        """
        newest = (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
            .all()
        )

        return list(reversed(newest))

    def previews(
        self,
        conversation_ids: list[UUID],
    ) -> dict[UUID, str]:
        """
        The last thing said in each thread, in one query.

        An inbox of forty rows should not be forty queries, and
        the alternative - keeping a copy of the last body on the
        conversation - is a denormalisation that goes stale the
        first time anything edits or removes a message.
        """
        if not conversation_ids:
            return {}

        newest = (
            self.db.query(
                Message.conversation_id,
                func.max(Message.created_at).label("at"),
            )
            .filter(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
            .subquery()
        )

        rows = (
            self.db.query(Message.conversation_id, Message.body)
            .join(
                newest,
                (Message.conversation_id == newest.c.conversation_id)
                & (Message.created_at == newest.c.at),
            )
            .all()
        )

        return {row[0]: row[1] for row in rows}

    def count_requests(
        self,
        workspace_id: UUID,
        user_id: UUID | None,
    ) -> int:
        return len(
            self.list_for(workspace_id, user_id, requests=True)
        )

    def add_message(self, message: Message) -> Message:
        self.db.add(message)
        return message

    def sent_since(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """How many messages this side has sent in this thread."""
        return (
            self.db.query(func.count(Message.id))
            .filter(
                Message.conversation_id == conversation_id,
                Message.sender_workspace_id == workspace_id,
            )
            .scalar()
            or 0
        )

    def has_replied(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
    ) -> bool:
        return self.sent_since(conversation_id, workspace_id) > 0

    def started_recently(
        self,
        workspace_id: UUID,
        since: datetime,
    ) -> int:
        return (
            self.db.query(func.count(self.model.id))
            .filter(
                self.model.started_by_workspace_id == workspace_id,
                self.model.created_at >= since,
            )
            .scalar()
            or 0
        )

    # ------------------------------------------------------------------
    # Read marks
    # ------------------------------------------------------------------

    def read_mark(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> ConversationRead | None:
        return (
            self.db.query(ConversationRead)
            .filter(
                ConversationRead.conversation_id == conversation_id,
                ConversationRead.user_id == user_id,
            )
            .first()
        )

    def unread_counts(
        self,
        conversation_ids: list[UUID],
        user_id: UUID,
        workspace_id: UUID,
    ) -> dict[UUID, int]:
        """
        How many messages in each thread this person has not seen.

        One query for the whole inbox rather than one per row.
        Messages this workspace sent itself never count: nobody
        needs telling about what their own side said.
        """
        if not conversation_ids:
            return {}

        marks = {
            mark.conversation_id: mark.read_through
            for mark in self.db.query(ConversationRead)
            .filter(
                ConversationRead.conversation_id.in_(conversation_ids),
                ConversationRead.user_id == user_id,
            )
            .all()
        }

        rows = (
            self.db.query(
                Message.conversation_id,
                Message.created_at,
            )
            .filter(
                Message.conversation_id.in_(conversation_ids),
                Message.sender_workspace_id != workspace_id,
            )
            .all()
        )

        counts: dict[UUID, int] = {}

        for conversation_id, sent_at in rows:
            mark = marks.get(conversation_id)

            if mark is None or as_utc(sent_at) > as_utc(mark):
                counts[conversation_id] = (
                    counts.get(conversation_id, 0) + 1
                )

        return counts

    # ------------------------------------------------------------------
    # Blocks
    # ------------------------------------------------------------------

    def block_between(
        self,
        one: UUID,
        other: UUID,
    ) -> WorkspaceBlock | None:
        """
        A block in either direction.

        Either direction, because a block stops the conversation
        rather than one person's half of it: being able to keep
        writing to somebody who has blocked you is not much of a
        block, and being unable to read their reply while they
        read yours is worse than silence.
        """
        return (
            self.db.query(WorkspaceBlock)
            .filter(
                or_(
                    (WorkspaceBlock.blocker_workspace_id == one)
                    & (WorkspaceBlock.blocked_workspace_id == other),
                    (WorkspaceBlock.blocker_workspace_id == other)
                    & (WorkspaceBlock.blocked_workspace_id == one),
                ),
                WorkspaceBlock.deleted_at.is_(None),
            )
            .first()
        )

    def block_by(
        self,
        blocker_workspace_id: UUID,
        blocked_workspace_id: UUID,
    ) -> WorkspaceBlock | None:
        """Including a lifted one, so unblocking and reblocking reuses it."""
        return (
            self.db.query(WorkspaceBlock)
            .filter(
                WorkspaceBlock.blocker_workspace_id
                == blocker_workspace_id,
                WorkspaceBlock.blocked_workspace_id
                == blocked_workspace_id,
            )
            .first()
        )

    def seen_by_other(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
    ) -> datetime | None:
        """
        How far the far end has read, for the "Seen" mark.

        The latest mark of anybody over there: an agency thread
        is read by whoever opens it, and from the creator's side
        "somebody at TalentX has read this" is the honest claim -
        naming which of them would be more than they asked.
        """
        rows = (
            self.db.query(ConversationRead.read_through)
            .join(
                WorkspaceMember,
                WorkspaceMember.user_id == ConversationRead.user_id,
            )
            .filter(
                ConversationRead.conversation_id == conversation_id,
                WorkspaceMember.workspace_id != workspace_id,
                WorkspaceMember.deleted_at.is_(None),
            )
            .all()
        )

        marks = [row[0] for row in rows if row[0] is not None]

        if not marks:
            return None

        return max(marks, key=as_utc)

    def add_block(self, block: WorkspaceBlock) -> WorkspaceBlock:
        self.db.add(block)
        return block

    def blocks_by(
        self,
        workspace_id: UUID,
    ) -> list[WorkspaceBlock]:
        return (
            self.db.query(WorkspaceBlock)
            .options(joinedload(WorkspaceBlock.blocked))
            .filter(
                WorkspaceBlock.blocker_workspace_id == workspace_id,
                WorkspaceBlock.deleted_at.is_(None),
            )
            .order_by(WorkspaceBlock.created_at.desc())
            .all()
        )
