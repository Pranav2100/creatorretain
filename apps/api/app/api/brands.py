from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_brand_service
from app.api.errors import http_error
from app.database.models.user import User
from app.schemas.workspace import BrandProfile, TrackRecord
from app.services.brand import BrandService

router = APIRouter(
    prefix="/brands",
    tags=["Brands"],
)


@router.get(
    "/{slug}",
    response_model=BrandProfile,
)
def get_brand(
    slug: str,
    # Signed in, but no plan gate and no relationship required.
    # Checking who is about to hire you is not a premium feature,
    # and a creator should be able to look before the offer lands.
    current_user: User = Depends(get_current_user),
    service: BrandService = Depends(get_brand_service),
):
    try:
        workspace = service.get_public(slug)
        record = service.track_record(workspace)

        return BrandProfile(
            id=workspace.id,
            slug=workspace.slug,
            display_name=workspace.display_name,
            workspace_type=workspace.workspace_type,
            verification_status=workspace.verification_status,
            legal_name=workspace.legal_name,
            bio=workspace.bio,
            logo_url=workspace.logo_url,
            website_url=workspace.website_url,
            track_record=TrackRecord(
                live_retainers=record.live_retainers,
                creators_worked_with=record.creators_worked_with,
                member_since=record.member_since,
                typical_review_hours=record.typical_review_hours,
                reviews_counted=record.reviews_counted,
            ),
        )

    except ValueError as e:
        raise http_error(e)
