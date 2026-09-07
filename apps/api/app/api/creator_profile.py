from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import (
    get_creator_profile_service,
)
from app.api.errors import http_error
from app.database.models.user import User
from app.schemas.creator_profile import (
    CategoryListResponse,
    CategoryResponse,
    CreatorProfileResponse,
    PortfolioItemRequest,
    PortfolioItemResponse,
    ProfileMessageResponse,
    RateRequest,
    RateResponse,
    SetCategoriesRequest,
    SetVisibilityRequest,
    SocialAccountRequest,
    SocialAccountResponse,
    UpdatePortfolioItemRequest,
    UpdateProfileRequest,
    UpdateRateRequest,
    UpdateSocialAccountRequest,
)
from app.services.creator_profile import CreatorProfileService

router = APIRouter(
    prefix="/creator-profile",
    tags=["Creator Profile"],
)

categories_router = APIRouter(
    prefix="/content-categories",
    tags=["Creator Profile"],
)


def _serialise(
    profile,
    service: CreatorProfileService,
) -> CreatorProfileResponse:
    return CreatorProfileResponse(
        id=profile.id,
        workspace_id=profile.workspace_id,
        headline=profile.headline,
        bio=profile.bio,
        city=profile.city,
        country=profile.country,
        languages=profile.languages or [],
        skills=profile.skills or [],
        monthly_retainer_min=profile.monthly_retainer_min,
        currency=profile.currency,
        availability=profile.availability,
        verification_status=profile.verification_status,
        status=profile.status,
        is_hidden=profile.is_hidden,
        is_discoverable=profile.is_discoverable,
        completeness=profile.completeness,
        missing_fields=service.missing_fields(profile),
        categories=[
            CategoryResponse.model_validate(category)
            for category in profile.categories
        ],
        social_accounts=[
            SocialAccountResponse.model_validate(account)
            for account in profile.social_accounts
        ],
        portfolio_items=[
            PortfolioItemResponse.model_validate(item)
            for item in profile.portfolio_items
        ],
        rates=[
            RateResponse.model_validate(rate)
            for rate in profile.rates
        ],
    )


@categories_router.get(
    "",
    response_model=CategoryListResponse,
)
def list_categories(
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    categories = service.list_categories()

    return CategoryListResponse(
        categories=[
            CategoryResponse.model_validate(category)
            for category in categories
        ]
    )


@router.get(
    "/me",
    response_model=CreatorProfileResponse,
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        profile = service.get_or_create(current_user.id)

        return _serialise(profile, service)

    except ValueError as e:
        raise http_error(e)


@router.put(
    "",
    response_model=CreatorProfileResponse,
)
def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        profile = service.update_basics(
            current_user.id,
            **request.model_dump(exclude_unset=True),
        )

        return _serialise(profile, service)

    except ValueError as e:
        raise http_error(e)


@router.put(
    "/categories",
    response_model=CreatorProfileResponse,
)
def set_categories(
    request: SetCategoriesRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        profile = service.set_categories(
            current_user.id,
            request.category_ids,
        )

        return _serialise(profile, service)

    except ValueError as e:
        raise http_error(e)


@router.patch(
    "/visibility",
    response_model=CreatorProfileResponse,
)
def set_visibility(
    request: SetVisibilityRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        profile = service.set_visibility(
            current_user.id,
            request.is_hidden,
        )

        return _serialise(profile, service)

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# Social accounts
# ----------------------------------------------------------------------


@router.post(
    "/social-accounts",
    response_model=SocialAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_social_account(
    request: SocialAccountRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        account = service.add_social_account(
            current_user.id,
            **request.model_dump(),
        )

        return SocialAccountResponse.model_validate(account)

    except ValueError as e:
        raise http_error(e)


@router.patch(
    "/social-accounts/{account_id}",
    response_model=SocialAccountResponse,
)
def update_social_account(
    account_id: UUID,
    request: UpdateSocialAccountRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        account = service.update_social_account(
            current_user.id,
            account_id,
            **request.model_dump(exclude_unset=True),
        )

        return SocialAccountResponse.model_validate(account)

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/social-accounts/{account_id}",
    response_model=ProfileMessageResponse,
)
def remove_social_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        service.remove_social_account(current_user.id, account_id)

        return ProfileMessageResponse(
            message="Social account removed.",
        )

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# Portfolio
# ----------------------------------------------------------------------


@router.post(
    "/portfolio",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_portfolio_item(
    request: PortfolioItemRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        item = service.add_portfolio_item(
            current_user.id,
            **request.model_dump(),
        )

        return PortfolioItemResponse.model_validate(item)

    except ValueError as e:
        raise http_error(e)


@router.patch(
    "/portfolio/{item_id}",
    response_model=PortfolioItemResponse,
)
def update_portfolio_item(
    item_id: UUID,
    request: UpdatePortfolioItemRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        item = service.update_portfolio_item(
            current_user.id,
            item_id,
            **request.model_dump(exclude_unset=True),
        )

        return PortfolioItemResponse.model_validate(item)

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/portfolio/{item_id}",
    response_model=ProfileMessageResponse,
)
def remove_portfolio_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        service.remove_portfolio_item(current_user.id, item_id)

        return ProfileMessageResponse(
            message="Portfolio item removed.",
        )

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# Rates
# ----------------------------------------------------------------------


@router.post(
    "/rates",
    response_model=RateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_rate(
    request: RateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        rate = service.add_rate(
            current_user.id,
            **request.model_dump(),
        )

        return RateResponse.model_validate(rate)

    except ValueError as e:
        raise http_error(e)


@router.patch(
    "/rates/{rate_id}",
    response_model=RateResponse,
)
def update_rate(
    rate_id: UUID,
    request: UpdateRateRequest,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        rate = service.update_rate(
            current_user.id,
            rate_id,
            **request.model_dump(exclude_unset=True),
        )

        return RateResponse.model_validate(rate)

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/rates/{rate_id}",
    response_model=ProfileMessageResponse,
)
def remove_rate(
    rate_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CreatorProfileService = Depends(
        get_creator_profile_service,
    ),
):
    try:
        service.remove_rate(current_user.id, rate_id)

        return ProfileMessageResponse(message="Rate removed.")

    except ValueError as e:
        raise http_error(e)
