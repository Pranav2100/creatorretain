from uuid import UUID

from app.common.utils import generate_slug
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
            raise ValueError("You already own a workspace.")

        slug = generate_slug(request.display_name)

        if self.repository.slug_exists(slug):
            raise ValueError("Workspace slug already exists.")

        workspace = Workspace(
            owner_user_id=owner_user_id,
            display_name=request.display_name,
            legal_name=request.legal_name,
            slug=slug,
            workspace_type=request.workspace_type,
            bio=request.bio,
        )

        return self.repository.create(workspace)