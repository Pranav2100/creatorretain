from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.database.models.message import MAX_MESSAGE_LENGTH


class SendMessageRequest(BaseModel):
    """
    Addressed either way round.

    `to_workspace_id` for the first message to somebody, which
    opens the thread; `conversation_id` for every one after. One
    endpoint for both, because the block check and the limits
    have to apply to each and two endpoints would be two places
    to forget them.
    """

    body: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    to_workspace_id: UUID | None = None
    conversation_id: UUID | None = None


class BlockRequest(BaseModel):
    workspace_id: UUID
    reason: str | None = Field(default=None, max_length=300)


class Correspondent(BaseModel):
    """The workspace at the other end."""

    workspace_id: UUID
    slug: str
    display_name: str
    logo_url: str | None = None

    # Carried because the two kinds live at different addresses:
    # a brand has a public page at its slug and a creator does
    # not, so without this the page has to guess and sometimes
    # links somewhere that is not there.
    workspace_type: str


class MessageResponse(BaseModel):
    id: UUID
    body: str
    at: datetime

    # Who said it, and which side they said it from.
    sender_name: str | None
    sender_person: str | None
    mine: bool

    @classmethod
    def seen_by(
        cls,
        message,
        workspace_id: UUID,
    ) -> "MessageResponse":
        sender = message.sender

        return cls(
            id=message.id,
            body=message.body,
            at=message.created_at,
            sender_name=message.sender_name,
            sender_person=(
                f"{sender.first_name} {sender.last_name}".strip()
                if sender is not None
                else None
            ),
            mine=message.sender_workspace_id == workspace_id,
        )


class ConversationSummary(BaseModel):
    id: UUID
    other: Correspondent
    last_message_at: datetime | None
    message_count: int
    unread: int

    # A line of the last thing said, so an inbox reads like an
    # inbox rather than a list of names.
    preview: str | None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total: int
    unread_total: int

    # How many strangers are waiting, so the inbox can carry the
    # Requests tab without fetching the other list to count it.
    requests_waiting: int


class ConversationDetail(BaseModel):
    id: UUID
    other: Correspondent
    messages: list[MessageResponse]

    # Whether anything can be sent. False once either side has
    # blocked the other; the reason is deliberately the same
    # either way round.
    open: bool

    # Still waiting on this reader to let it in. The sender never
    # sees this as true - from where they sit they have written
    # to somebody, which is what they did.
    is_request: bool

    # Whether this reader started it, which decides whether the
    # page says "waiting for them to accept" or offers Accept
    # and Delete.
    started_by_me: bool

    # How far the far end has read. Null when they have not
    # opened it, or have no mark yet.
    seen_at: datetime | None


class UnreadResponse(BaseModel):
    """
    What the header carries on every page.

    Requests are counted separately and deliberately not added
    in: a badge a stranger can raise is a badge nobody trusts.
    """

    unread: int
    requests: int


class BlockedWorkspace(BaseModel):
    workspace_id: UUID
    display_name: str
    blocked_at: datetime


class BlockListResponse(BaseModel):
    blocked: list[BlockedWorkspace]
    total: int


def correspondent(workspace) -> Correspondent:
    return Correspondent(
        workspace_id=workspace.id,
        slug=workspace.slug,
        display_name=workspace.display_name,
        logo_url=getattr(workspace, "logo_url", None),
        workspace_type=str(
            getattr(
                workspace.workspace_type,
                "value",
                workspace.workspace_type,
            )
        ),
    )
