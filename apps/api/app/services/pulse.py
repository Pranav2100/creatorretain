from datetime import datetime
from enum import Enum
from uuid import UUID

from app.common.permissions import WorkspacePermission
from app.database.repositories.pulse import EMPTY, PulseRepository
from app.services.workspace_member import WorkspaceMemberService


class Watchable(str, Enum):
    """
    The kinds of thing a page can be showing.

    Named for what the reader is looking at rather than for the
    tables underneath, because a page knows the first and should
    not have to know the second. Adding a page means adding a
    name here and a reading in the repository, not teaching every
    caller about schema.
    """

    RETAINERS = "retainers"
    WORKSPACE = "workspace"
    PROFILE = "profile"
    CREATOR = "creator"
    DISCOVERY = "discovery"
    MESSAGES = "messages"


class PulseService:
    """
    One number a page can watch, assembled from what it declared.

    Deliberately thin. Everything here is an aggregate over rows
    the caller can already see, so there is no authorisation
    question beyond "which workspace is this" - and that is
    resolved once, at the top.
    """

    def __init__(
        self,
        repository: PulseRepository,
        member_service: WorkspaceMemberService,
    ):
        self.repository = repository
        self.member_service = member_service

    def read(
        self,
        current_user_id: UUID,
        scopes: list[Watchable],
        *,
        retainer_id: UUID | None = None,
        creator_workspace_id: UUID | None = None,
    ) -> tuple[datetime | None, int]:
        context = self.member_service.resolve_context(current_user_id)
        workspace_id = context.workspace_id

        # Someone who only sees the retainers assigned to them
        # should only be told when those change. The watcher is
        # narrowed by the same rule as the pages it watches.
        assigned_to = (
            None
            if context.allows(
                WorkspacePermission.VIEW_ALL_RETAINERS
            )
            else current_user_id
        )

        readings = []

        for scope in dict.fromkeys(scopes):
            readings.append(
                self._one(
                    scope,
                    workspace_id,
                    retainer_id,
                    creator_workspace_id,
                    assigned_to,
                )
            )

        return self.repository.combine(readings)

    def _one(
        self,
        scope: Watchable,
        workspace_id: UUID,
        retainer_id: UUID | None,
        creator_workspace_id: UUID | None,
        assigned_to: UUID | None = None,
    ):
        if scope == Watchable.RETAINERS:
            return self.repository.retainers(
                workspace_id,
                retainer_id,
                assigned_to,
            )

        if scope == Watchable.MESSAGES:
            return self.repository.messages(workspace_id, assigned_to)

        if scope == Watchable.WORKSPACE:
            return self.repository.workspace(workspace_id)

        if scope == Watchable.PROFILE:
            return self.repository.profile(workspace_id)

        if scope == Watchable.CREATOR:
            # Without an id there is no creator to watch. Reading
            # nothing is right here: a page that asked badly gets
            # a steady answer rather than one that never settles.
            if creator_workspace_id is None:
                return EMPTY

            return self.repository.creator(creator_workspace_id)

        return self.repository.discovery()
