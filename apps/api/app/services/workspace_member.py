import uuid

from app.common.enums import (
    WorkspaceMemberStatus,
    WorkspaceRole,
)
from app.database.models.workspace_member import WorkspaceMember
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)


class WorkspaceMemberService:
    def __init__(
        self,
        repository: WorkspaceMemberRepository,
    ):
        self.repository = repository

    def create_owner(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
            status=WorkspaceMemberStatus.ACTIVE,
        )

        return self.repository.create(member)