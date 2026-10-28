from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_conversation_service
from app.api.errors import http_error
from app.database.models.user import User
from app.schemas.conversation import (
    BlockListResponse,
    BlockRequest,
    BlockedWorkspace,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    MessageResponse,
    SendMessageRequest,
    UnreadResponse,
    correspondent,
)
from app.services.conversation import ConversationService

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="Your conversations, newest first",
)
def inbox(
    requests: bool = Query(
        default=False,
        description="The other pile: strangers waiting to be let in.",
    ),
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        conversations, unread, workspace_id = service.inbox(
            current_user.id,
            requests=requests,
        )

        previews = service.repository.previews(
            [c.id for c in conversations]
        )

        rows = [
            ConversationSummary(
                id=c.id,
                other=correspondent(
                    c.higher_workspace
                    if c.lower_workspace_id == workspace_id
                    else c.lower_workspace
                ),
                last_message_at=c.last_message_at,
                message_count=c.message_count,
                unread=unread.get(c.id, 0),
                preview=previews.get(c.id),
            )
            for c in conversations
        ]

        return ConversationListResponse(
            conversations=rows,
            total=len(rows),
            unread_total=sum(r.unread for r in rows),
            requests_waiting=service.waiting(current_user.id),
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    responses={404: {"description": "Not found"}},
    summary="One thread",
)
def thread(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        conversation, messages, workspace_id = service.thread(
            current_user.id,
            conversation_id,
        )

        other = (
            conversation.higher_workspace
            if conversation.lower_workspace_id == workspace_id
            else conversation.lower_workspace
        )

        blocked = service.repository.block_between(
            workspace_id,
            other.id,
        )

        return ConversationDetail(
            id=conversation.id,
            other=correspondent(other),
            messages=[
                MessageResponse.seen_by(m, workspace_id)
                for m in messages
            ],
            open=blocked is None and (
                conversation.declined_at is None
                or conversation.started_by_workspace_id
                != workspace_id
            ),
            is_request=conversation.is_request_for(workspace_id),
            started_by_me=(
                conversation.started_by_workspace_id == workspace_id
            ),
            seen_at=service.repository.seen_by_other(
                conversation.id,
                workspace_id,
            ),
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/messages",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Could not be delivered"},
        409: {"description": "Refused"},
    },
    summary="Say something, opening the thread if there is not one",
)
def send(
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        conversation, _ = service.send(
            current_user.id,
            to_workspace_id=payload.to_workspace_id,
            conversation_id=payload.conversation_id,
            body=payload.body,
        )

        return thread(conversation.id, current_user, service)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{conversation_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark this thread read up to now",
)
def mark_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        service.mark_read(current_user.id, conversation_id)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{conversation_id}/accept",
    response_model=ConversationDetail,
    responses={409: {"description": "Not waiting on you"}},
    summary="Let a request into your inbox",
)
def accept(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        service.accept(current_user.id, conversation_id)

        return thread(conversation_id, current_user, service)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{conversation_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={409: {"description": "Not waiting on you"}},
    summary="Turn a request away",
)
def decline(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        service.decline(current_user.id, conversation_id)

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/unread/count",
    response_model=UnreadResponse,
    summary="What the header badge shows",
)
def unread(
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Under /unread/count rather than /unread, so the one-segment
    route for a conversation id does not swallow it.
    """
    try:
        count, requests = service.badge(current_user.id)

        return UnreadResponse(unread=count, requests=requests)

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/blocks/list",
    response_model=BlockListResponse,
    summary="Who this workspace will not hear from",
)
def blocks(
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    Under /blocks/list rather than /blocks, because routes match
    in the order they are written and /{conversation_id} would
    otherwise swallow it.
    """
    try:
        found = service.blocked(current_user.id)

        return BlockListResponse(
            blocked=[
                BlockedWorkspace(
                    workspace_id=b.blocked_workspace_id,
                    display_name=b.blocked.display_name,
                    blocked_at=b.created_at,
                )
                for b in found
            ],
            total=len(found),
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/blocks",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop hearing from a workspace",
)
def block(
    payload: BlockRequest,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        service.block(
            current_user.id,
            payload.workspace_id,
            payload.reason,
        )

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/blocks/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undo a block",
)
def unblock(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    try:
        service.unblock(current_user.id, workspace_id)

    except ValueError as e:
        raise http_error(e)
