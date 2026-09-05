from uuid import UUID

from app.common.exceptions import ConflictError, NotFoundError
from app.common.validators import validate_username
from app.database.models.workspace import Workspace
from app.database.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import CreateWorkspaceRequest
from app.services.workspace_member import WorkspaceMemberService


class WorkspaceService:
    def __init__(
        self,
        repository: WorkspaceRepository,
        member_service: WorkspaceMemberService,
    ):
        self.repository = repository
        self.member_service = member_service

    def create(
        self,
        owner_user_id: UUID,
        request: CreateWorkspaceRequest,
    ) -> Workspace:
        existing_workspace = self.repository.get_by_owner(owner_user_id)

        if existing_workspace:
            raise ConflictError(
                "You already own a workspace."
            )

        existing_membership = (
            self.member_service.get_active_membership(
                owner_user_id,
            )
        )

        if existing_membership:
            raise ConflictError(
                "You already belong to a workspace. Leave it before "
                "creating a new one."
            )

        validate_username(request.username)

        if self.repository.slug_exists(request.username):
            raise ValueError(
                "Username is already taken."
            )

        workspace = Workspace(
            owner_user_id=owner_user_id,
            display_name=request.display_name,
            legal_name=request.legal_name,
            slug=request.username,
            workspace_type=request.workspace_type,
            bio=request.bio,
        )

        workspace = self.repository.create(workspace)

        self.member_service.create_owner(
            workspace_id=workspace.id,
            user_id=owner_user_id,
        )

        return workspace

    def check_username(self, username: str) -> dict:
        try:
            validate_username(username)
        except ValueError as e:
            return {
                "available": False,
                "message": str(e),
                "suggestions": [],
            }

        if self.repository.slug_exists(username):
            return {
                "available": False,
                "message": "Username is already taken.",
                "suggestions": [
                    f"{username}07",
                    f"{username}_",
                    f"its{username}",
                    f"official{username}",
                    f"{username}1",
                ],
            }

        return {
            "available": True,
            "message": "Username is available.",
            "suggestions": [],
        }

    def get_my_workspace(
        self,
        current_user_id: UUID,
    ) -> Workspace:
        """
        Resolves through active membership, so Admins and Members
        see the workspace they belong to, not only Owners.
        """
        context = self.member_service.resolve_context(
            current_user_id,
        )

        if context.workspace is None:
            raise NotFoundError("Workspace not found.")

        return context.workspace