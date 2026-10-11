from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_discovery_service
from app.api.errors import http_error
from app.common.enums import CreatorAvailability, SocialPlatform
from app.database.models.user import User
from app.schemas.discovery import (
    CreatorCard,
    CreatorDetail,
    DiscoveryResponse,
)
from app.services.discovery import (
    DEFAULT_PAGE_SIZE,
    DiscoveryFilters,
    DiscoveryService,
)

router = APIRouter(
    prefix="/discovery",
    tags=["Discovery"],
)


@router.get(
    "/creators",
    response_model=DiscoveryResponse,
)
def search_creators(
    category: list[str] | None = Query(
        default=None,
        description="Category slugs. Repeat for several.",
    ),
    platform: SocialPlatform | None = None,
    min_followers: int | None = Query(default=None, ge=0),
    max_followers: int | None = Query(default=None, ge=0),
    min_engagement_rate: Decimal | None = Query(
        default=None,
        ge=0,
        le=100,
        description="Pro and above.",
    ),
    country: str | None = Query(
        default=None,
        min_length=2,
        max_length=2,
    ),
    city: str | None = Query(default=None, description="Pro and above."),
    language: list[str] | None = Query(
        default=None,
        description="ISO 639-1 codes. Pro and above.",
    ),
    max_monthly_retainer: Decimal | None = Query(
        default=None,
        ge=0,
        description="Pro and above.",
    ),
    availability: CreatorAvailability | None = None,
    verified_only: bool = Query(
        default=False,
        description="Pro and above.",
    ),
    offset: int = Query(default=0, ge=0),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: DiscoveryService = Depends(get_discovery_service),
):
    filters = DiscoveryFilters(
        category_slugs=category,
        platform=platform,
        min_followers=min_followers,
        max_followers=max_followers,
        min_engagement_rate=min_engagement_rate,
        country=country,
        city=city,
        languages=language,
        max_monthly_retainer=max_monthly_retainer,
        availability=availability,
        verified_only=verified_only,
    )

    try:
        result = service.search(
            current_user.id,
            filters,
            offset=offset,
            page_size=page_size,
        )

        return DiscoveryResponse(
            results=[
                CreatorCard.from_profile(profile)
                for profile in result.profiles
            ],
            total_matching=result.total_matching,
            returned=result.returned,
            offset=result.offset,
            result_cap=result.result_cap,
            capped=result.capped,
            can_contact=result.can_contact,
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/creators/{profile_id}",
    response_model=CreatorDetail,
)
def get_creator(
    profile_id: UUID,
    current_user: User = Depends(get_current_user),
    service: DiscoveryService = Depends(get_discovery_service),
):
    try:
        profile, can_contact = service.get_profile(
            current_user.id,
            profile_id,
        )

        return CreatorDetail.from_profile_detail(profile, can_contact)

    except ValueError as e:
        raise http_error(e)
