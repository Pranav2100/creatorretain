import logging
from uuid import UUID, uuid4

from app.common.exceptions import ConflictError, NotFoundError
from app.common.permissions.workspace import WorkspacePermission
from app.common.utils.images import sniff_image
from app.common.validators import validate_username
from app.database.models.workspace import Workspace
from app.database.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import CreateWorkspaceRequest
from app.services.storage.base import FileStore
from app.services.workspace_member import WorkspaceMemberService

logger = logging.getLogger(__name__)


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

    def update(
        self,
        current_user_id: UUID,
        **fields,
    ) -> Workspace:
        """
        Applies exactly the fields that were sent.

        The caller passes only what the request actually carried, so
        an explicit null clears a field and an absent one leaves it
        alone. That is the whole point: taking a bad logo down has
        to be possible, and "" and "unchanged" cannot be the same
        thing.
        """
        context = self.member_service.resolve_context(current_user_id)

        if context.workspace is None:
            raise NotFoundError("Workspace not found.")

        context.require(
            WorkspacePermission.EDIT_WORKSPACE,
            "Only the owner and admins can change the workspace.",
        )

        if "display_name" in fields and not fields["display_name"]:
            raise ValueError("A workspace needs a name.")

        for key, value in fields.items():
            setattr(context.workspace, key, value)

        return self.repository.save(context.workspace)

    def set_logo(
        self,
        current_user_id: UUID,
        *,
        data: bytes,
        file_store: FileStore,
    ) -> Workspace:
        """
        Replaces the workspace logo with an uploaded image.

        What the browser called the file is ignored entirely. The
        type comes from the bytes, and the stored name is built
        here, so an uploader controls the picture and nothing else
        about where it lands.
        """
        context = self.member_service.resolve_context(current_user_id)

        if context.workspace is None:
            raise NotFoundError("Workspace not found.")

        context.require(
            WorkspacePermission.EDIT_WORKSPACE,
            "Only the owner and admins can change the workspace.",
        )

        content_type, extension = sniff_image(data)

        workspace = context.workspace
        previous = workspace.logo_storage_key

        # A fresh name every time rather than one fixed path per
        # workspace: caches and CDNs key on the URL, and a logo
        # that silently refuses to change for a day is worse than
        # a tidy filename.
        key = (
            f"workspace-logos/{workspace.id}/"
            f"{uuid4().hex}.{extension}"
        )

        stored = file_store.save(
            key=key,
            data=data,
            content_type=content_type,
        )

        workspace.logo_url = stored.url
        workspace.logo_storage_key = stored.key

        saved = self.repository.save(workspace)

        # Only after the new one is safely recorded. Losing the old
        # file matters far less than a row pointing at nothing.
        if previous and previous != stored.key:
            self._discard(file_store, previous)

        return saved

    def clear_logo(
        self,
        current_user_id: UUID,
        *,
        file_store: FileStore,
    ) -> Workspace:
        context = self.member_service.resolve_context(current_user_id)

        if context.workspace is None:
            raise NotFoundError("Workspace not found.")

        context.require(
            WorkspacePermission.EDIT_WORKSPACE,
            "Only the owner and admins can change the workspace.",
        )

        workspace = context.workspace
        previous = workspace.logo_storage_key

        workspace.logo_url = None
        workspace.logo_storage_key = None

        saved = self.repository.save(workspace)

        if previous:
            self._discard(file_store, previous)

        return saved

    @staticmethod
    def _discard(file_store: FileStore, key: str) -> None:
        """
        A leftover file is untidy; a failed request because tidying
        up went wrong is a bug the person can see. The row is
        already correct by this point either way.
        """
        try:
            file_store.delete(key)
        except Exception:  # noqa: BLE001
            logger.warning("Could not remove old upload %s", key)

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
        return self.my_context(current_user_id).workspace

    def my_context(self, current_user_id: UUID):
        """The same resolution, keeping the role along with it."""
        context = self.member_service.resolve_context(
            current_user_id,
        )

        if context.workspace is None:
            raise NotFoundError("Workspace not found.")

        return context