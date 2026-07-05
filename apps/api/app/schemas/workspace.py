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

    username: str = Field(
        min_length=3,
        max_length=30,
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
    slug: str
    workspace_type: WorkspaceType
    verification_status: VerificationStatus
    status: WorkspaceStatus
    legal_name: str | None
    bio: str | None
    logo_url: str | None
    banner_url: str | None


class CreateWorkspaceResponse(BaseModel):
    message: str
    workspace: WorkspaceResponse