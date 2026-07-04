from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import (
    VerificationStatus,
    WorkspaceStatus,
    WorkspaceType,
)


class CreateWorkspaceRequest(BaseModel):
    display_name: str = Field(
        min_length=2,
        max_length=100,
    )

    workspace_type: WorkspaceType

    legal_name: str | None = Field(
        default=None,
        max_length=200,
    )

    bio: str | None = Field(
        default=None,
        max_length=500,
    )


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    owner_user_id: UUID

    display_name: str

    legal_name: str | None

    slug: str

    workspace_type: WorkspaceType

    verification_status: VerificationStatus

    status: WorkspaceStatus

    bio: str | None

    logo_url: str | None

    banner_url: str | None


class CreateWorkspaceResponse(BaseModel):
    message: str

    workspace: WorkspaceResponse