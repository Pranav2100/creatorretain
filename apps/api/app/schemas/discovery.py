from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.common.enums import (
    CreatorAvailability,
    CreatorVerificationStatus,
    DeliverableType,
    SocialPlatform,
)
from app.database.models.creator_profile import CreatorProfile


class DiscoveryCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str


class DiscoveryPlatform(BaseModel):
    platform: SocialPlatform
    handle: str
    followers: int | None
    engagement_rate: Decimal | None
    is_verified: bool


class CreatorCard(BaseModel):
    """
    What a search result shows. Deliberately not the whole profile:
    no bio, portfolio or rate card until someone opens it.
    """

    id: UUID
    workspace_id: UUID
    slug: str
    display_name: str
    headline: str | None
    city: str | None
    country: str | None
    availability: CreatorAvailability
    verification_status: CreatorVerificationStatus
    is_boosted: bool
    completeness: int
    monthly_retainer_min: Decimal | None
    currency: str
    top_followers: int | None
    categories: list[DiscoveryCategory]
    platforms: list[DiscoveryPlatform]

    @classmethod
    def from_profile(cls, profile: CreatorProfile) -> "CreatorCard":
        platforms = [
            DiscoveryPlatform(
                platform=account.platform,
                handle=account.handle,
                followers=account.followers,
                engagement_rate=account.engagement_rate,
                is_verified=account.is_verified,
            )
            for account in profile.social_accounts
        ]

        platforms.sort(
            key=lambda p: p.followers or 0,
            reverse=True,
        )

        return cls(
            id=profile.id,
            workspace_id=profile.workspace_id,
            slug=profile.workspace.slug,
            display_name=profile.workspace.display_name,
            headline=profile.headline,
            city=profile.city,
            country=profile.country,
            availability=profile.availability,
            verification_status=profile.verification_status,
            is_boosted=profile.is_boosted,
            completeness=profile.completeness,
            monthly_retainer_min=profile.monthly_retainer_min,
            currency=profile.currency,
            top_followers=platforms[0].followers if platforms else None,
            categories=[
                DiscoveryCategory.model_validate(category)
                for category in profile.categories
            ],
            platforms=platforms,
        )


class DiscoveryResponse(BaseModel):
    results: list[CreatorCard]
    total_matching: int
    returned: int
    offset: int

    # Null when the plan has no ceiling. When set, total_matching is
    # still the true figure - the gap is what upgrading buys.
    result_cap: int | None
    capped: bool
    can_contact: bool


class DiscoveryPortfolioItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None
    platform: SocialPlatform | None
    external_url: str | None
    media_url: str | None


class DiscoveryRate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deliverable_type: DeliverableType
    quantity: int
    price: Decimal
    currency: str
    notes: str | None


class CreatorDetail(CreatorCard):
    bio: str | None
    languages: list[str]
    skills: list[str]
    verified_at: datetime | None
    portfolio_items: list[DiscoveryPortfolioItem]
    rates: list[DiscoveryRate]
    can_contact: bool

    @classmethod
    def from_profile_detail(
        cls,
        profile: CreatorProfile,
        can_contact: bool,
    ) -> "CreatorDetail":
        card = CreatorCard.from_profile(profile)

        return cls(
            **card.model_dump(),
            bio=profile.bio,
            languages=profile.languages or [],
            skills=profile.skills or [],
            verified_at=profile.verified_at,
            portfolio_items=[
                DiscoveryPortfolioItem.model_validate(item)
                for item in profile.portfolio_items
            ],
            rates=[
                DiscoveryRate.model_validate(rate)
                for rate in profile.rates
            ],
            can_contact=can_contact,
        )
