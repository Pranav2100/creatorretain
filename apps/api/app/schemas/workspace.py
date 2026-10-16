from datetime import datetime
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
)

from app.common.enums import (
    VerificationStatus,
    WorkspaceRole,
    WorkspaceStatus,
    WorkspaceType,
)

_URL = TypeAdapter(AnyHttpUrl)


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


class UpdateWorkspaceRequest(BaseModel):
    """
    Every field is optional and only what is sent is applied, so
    sending null genuinely clears a logo rather than being read as
    "leave it alone". That distinction matters here: taking a bad
    logo down has to be possible.

    The username is deliberately absent. A slug is the workspace's
    address, and changing it breaks every link anyone saved; that
    needs its own flow with its own warnings, not a quiet text box
    on a settings form.

    So is the logo. It is an uploaded file now, with its own
    endpoints, and letting this one also write logo_url would
    leave the stored file orphaned behind a row that no longer
    points at it.
    """

    display_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    legal_name: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)

    @field_validator("display_name", "legal_name", "bio")
    @classmethod
    def _tidy(cls, value: str | None) -> str | None:
        """A field typed full of spaces is an empty field."""
        if value is None:
            return None

        text = value.strip()

        return text or None

    @field_validator("website_url")
    @classmethod
    def _real_url(cls, value: str | None) -> str | None:
        """
        Declared as text because that is what the column holds, but
        checked as a URL so "my website" never ends up in an href.
        """
        if value is None:
            return None

        text = value.strip()

        if not text:
            return None

        try:
            _URL.validate_python(text)
        except ValidationError:
            raise ValueError(
                "Enter a full web address, starting with https://"
            ) from None

        return text


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
    website_url: str | None


class MyWorkspaceResponse(WorkspaceResponse):
    """
    The workspace plus where the reader stands in it.

    Same idea as `your_side` on a retainer: the client cannot show
    the right screen without knowing which seat the person is in,
    and making it work that out from a members list it may not even
    be allowed to fetch would be silly.
    """

    your_role: WorkspaceRole


class CreateWorkspaceResponse(BaseModel):
    message: str
    workspace: WorkspaceResponse


class TrackRecord(BaseModel):
    """
    What the platform can say about a hiring workspace that the
    workspace cannot say about itself.

    Every number here is counted from retainers and reviews at the
    moment it is asked for. Nothing is stored, so nothing can drift
    away from the truth, and nobody can type a better one in.
    """

    live_retainers: int
    creators_worked_with: int
    member_since: datetime

    # Median hours from a creator submitting to someone reviewing.
    # Null when too few reviews have happened to mean anything -
    # one fast review is not a habit.
    typical_review_hours: float | None
    reviews_counted: int


class BrandProfile(BaseModel):
    """
    A hiring workspace as a creator sees it: what they wrote about
    themselves, and what the platform has watched them do.

    Called a brand because that is the word the rest of the code
    uses for this side of a retainer - an agency hiring on behalf
    of a client sits in exactly the same place.
    """

    id: UUID
    slug: str
    display_name: str
    workspace_type: WorkspaceType
    verification_status: VerificationStatus
    legal_name: str | None
    bio: str | None
    logo_url: str | None
    website_url: str | None
    track_record: TrackRecord