from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import (
    CreatorAvailability,
    CreatorProfileStatus,
    CreatorVerificationStatus,
    DeliverableType,
    SocialPlatform,
)


class UpdateProfileRequest(BaseModel):
    headline: str | None = Field(default=None, max_length=120)
    bio: str | None = None
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2, e.g. IN",
    )
    languages: list[str] | None = None
    skills: list[str] | None = None
    monthly_retainer_min: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )
    availability: CreatorAvailability | None = None


class SetCategoriesRequest(BaseModel):
    category_ids: list[UUID] = Field(max_length=5)


class SetVisibilityRequest(BaseModel):
    is_hidden: bool


class SocialAccountRequest(BaseModel):
    platform: SocialPlatform
    handle: str = Field(max_length=100)
    profile_url: str | None = None
    claimed_followers: int | None = Field(default=None, ge=0)
    claimed_engagement_rate: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class UpdateSocialAccountRequest(BaseModel):
    handle: str | None = Field(default=None, max_length=100)
    profile_url: str | None = None
    claimed_followers: int | None = Field(default=None, ge=0)
    claimed_engagement_rate: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class PortfolioItemRequest(BaseModel):
    title: str = Field(max_length=150)
    description: str | None = None
    platform: SocialPlatform | None = None
    external_url: str | None = None
    media_url: str | None = None


class UpdatePortfolioItemRequest(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    description: str | None = None
    platform: SocialPlatform | None = None
    external_url: str | None = None
    media_url: str | None = None
    position: int | None = Field(default=None, ge=0)


class RateRequest(BaseModel):
    deliverable_type: DeliverableType
    price: Decimal = Field(gt=0)
    quantity: int = Field(default=1, ge=1)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=200)


class UpdateRateRequest(BaseModel):
    price: Decimal | None = Field(default=None, gt=0)
    quantity: int | None = Field(default=None, ge=1)
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )
    notes: str | None = Field(default=None, max_length=200)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str


class CategoryListResponse(BaseModel):
    categories: list[CategoryResponse]


class SocialAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: SocialPlatform
    handle: str
    profile_url: str | None
    claimed_followers: int | None
    claimed_engagement_rate: Decimal | None
    verified_followers: int | None
    verified_engagement_rate: Decimal | None
    verified_at: datetime | None
    is_verified: bool


class PortfolioItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    platform: SocialPlatform | None
    external_url: str | None
    media_url: str | None
    position: int


class RateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deliverable_type: DeliverableType
    quantity: int
    price: Decimal
    currency: str
    notes: str | None


class CreatorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    headline: str | None
    bio: str | None
    city: str | None
    country: str | None
    languages: list[str]
    skills: list[str]
    monthly_retainer_min: Decimal | None
    currency: str
    availability: CreatorAvailability
    verification_status: CreatorVerificationStatus
    status: CreatorProfileStatus
    is_hidden: bool
    is_discoverable: bool
    completeness: int
    missing_fields: list[str]
    categories: list[CategoryResponse]
    social_accounts: list[SocialAccountResponse]
    portfolio_items: list[PortfolioItemResponse]
    rates: list[RateResponse]


class ProfileMessageResponse(BaseModel):
    message: str
