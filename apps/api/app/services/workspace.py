from uuid import UUID

from app.common.validators import validate_username
from app.database.models.workspace import Workspace
from app.database.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import CreateWorkspaceRequest


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def create(
        self,
        owner_user_id: UUID,
        request: CreateWorkspaceRequest,
    ) -> Workspace:
        existing_workspace = self.repository.get_by_owner(owner_user_id)

        if existing_workspace:
            raise ValueError(
                "You already own a workspace."
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

        return self.repository.create(workspace)

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
        owner_user_id: UUID,
    ) -> Workspace:
        workspace = self.repository.get_my_workspace(owner_user_id)

        if workspace is None:
            raise ValueError(
                "Workspace not found."
            )

        return workspace