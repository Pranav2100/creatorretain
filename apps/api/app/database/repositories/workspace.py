from uuid import UUID

from sqlalchemy.orm import Session

from app.database.models.workspace import Workspace
from app.database.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, db: Session):
        super().__init__(db, Workspace)

    def get_by_slug(self, slug: str) -> Workspace | None:
        return (
            self.db.query(Workspace)
            .filter(
                Workspace.slug == slug,
                Workspace.deleted_at.is_(None),
            )
            .first()
        )

    def slug_exists(self, slug: str) -> bool:
        return self.get_by_slug(slug) is not None

    def get_by_owner(self, owner_user_id: UUID) -> Workspace | None:
        return (
            self.db.query(Workspace)
            .filter(
                Workspace.owner_user_id == owner_user_id,
                Workspace.deleted_at.is_(None),
            )
            .first()
        )

    def get_my_workspace(
        self,
        owner_user_id: UUID,
    ) -> Workspace | None:
        return self.get_by_owner(owner_user_id)