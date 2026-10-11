from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Integer, String, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.common.enums import (
    CreatorAvailability,
    CreatorProfileStatus,
    CreatorVerificationStatus,
    SocialPlatform,
)
from app.database.models.content_category import (
    ContentCategory,
    creator_categories,
)
from app.database.models.creator_profile import CreatorProfile
from app.database.models.creator_social_account import (
    CreatorSocialAccount,
)

# Relevance is completeness (0-100). Verification and boost add on
# top rather than overriding it, so a boosted thin profile still
# loses to a complete one: 60 + 25 = 85 against 100 + 15 = 115.
VERIFIED_BONUS = 15
BOOST_BONUS = 25


class DiscoveryRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Query construction
    # ------------------------------------------------------------------

    def _followers_expression(self):
        """Verified figure where it exists, otherwise the claim."""
        return func.coalesce(
            CreatorSocialAccount.verified_followers,
            CreatorSocialAccount.claimed_followers,
        )

    def _engagement_expression(self):
        return func.coalesce(
            CreatorSocialAccount.verified_engagement_rate,
            CreatorSocialAccount.claimed_engagement_rate,
        )

    def _rank_expression(self, now: datetime):
        verified = case(
            (
                CreatorProfile.verification_status
                == CreatorVerificationStatus.VERIFIED,
                VERIFIED_BONUS,
            ),
            else_=0,
        )

        boosted = case(
            (CreatorProfile.boosted_until > now, BOOST_BONUS),
            else_=0,
        )

        return (
            func.cast(CreatorProfile.completeness, Integer)
            + verified
            + boosted
        )

    def _base_query(self, exclude_workspace_id: UUID | None):
        query = self.db.query(CreatorProfile).filter(
            CreatorProfile.status == CreatorProfileStatus.PUBLISHED,
            CreatorProfile.is_hidden.is_(False),
            CreatorProfile.deleted_at.is_(None),
        )

        if exclude_workspace_id is not None:
            query = query.filter(
                CreatorProfile.workspace_id != exclude_workspace_id,
            )

        return query

    def _apply_filters(
        self,
        query,
        *,
        category_slugs: list[str] | None,
        platform: SocialPlatform | None,
        min_followers: int | None,
        max_followers: int | None,
        min_engagement_rate: Decimal | None,
        country: str | None,
        city: str | None,
        languages: list[str] | None,
        max_monthly_retainer: Decimal | None,
        availability: CreatorAvailability | None,
        verified_only: bool,
    ):
        if category_slugs:
            query = query.filter(
                CreatorProfile.id.in_(
                    select(creator_categories.c.profile_id)
                    .join(
                        ContentCategory,
                        ContentCategory.id
                        == creator_categories.c.category_id,
                    )
                    .where(ContentCategory.slug.in_(category_slugs))
                )
            )

        # One EXISTS covers platform, reach and engagement together,
        # so "50k+ on Instagram" cannot be satisfied by 50k on YouTube
        # and an Instagram handle with none.
        needs_account = (
            platform is not None
            or min_followers is not None
            or max_followers is not None
            or min_engagement_rate is not None
        )

        if needs_account:
            followers = self._followers_expression()
            engagement = self._engagement_expression()

            account = select(CreatorSocialAccount.id).where(
                CreatorSocialAccount.profile_id == CreatorProfile.id,
            )

            if platform is not None:
                account = account.where(
                    CreatorSocialAccount.platform == platform,
                )

            if min_followers is not None:
                account = account.where(followers >= min_followers)

            if max_followers is not None:
                account = account.where(followers <= max_followers)

            if min_engagement_rate is not None:
                account = account.where(
                    engagement >= min_engagement_rate,
                )

            query = query.filter(account.exists())

        if country:
            query = query.filter(
                CreatorProfile.country == country.upper(),
            )

        if city:
            query = query.filter(
                func.lower(CreatorProfile.city) == city.lower(),
            )

        if languages:
            # languages is a JSON list so the models run on both
            # Postgres and SQLite, which rules out a native array
            # operator. ISO 639-1 codes are exactly two characters,
            # so a quoted substring match against the serialised list
            # is exact - "en" cannot match inside another code.
            #
            # If language filtering ever gets heavy use it should
            # become a join table, the way categories already are.
            serialised = func.lower(
                func.cast(CreatorProfile.languages, String),
            )

            query = query.filter(
                or_(
                    *[
                        serialised.like(f'%"{code.lower()}"%')
                        for code in languages
                    ]
                )
            )

        if max_monthly_retainer is not None:
            query = query.filter(
                CreatorProfile.monthly_retainer_min.isnot(None),
                CreatorProfile.monthly_retainer_min
                <= max_monthly_retainer,
            )

        if availability is not None:
            query = query.filter(
                CreatorProfile.availability == availability,
            )

        if verified_only:
            query = query.filter(
                CreatorProfile.verification_status
                == CreatorVerificationStatus.VERIFIED,
            )

        return query

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def search(
        self,
        *,
        exclude_workspace_id: UUID | None = None,
        category_slugs: list[str] | None = None,
        platform: SocialPlatform | None = None,
        min_followers: int | None = None,
        max_followers: int | None = None,
        min_engagement_rate: Decimal | None = None,
        country: str | None = None,
        city: str | None = None,
        languages: list[str] | None = None,
        max_monthly_retainer: Decimal | None = None,
        availability: CreatorAvailability | None = None,
        verified_only: bool = False,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[CreatorProfile], int]:
        now = datetime.now(timezone.utc)

        query = self._apply_filters(
            self._base_query(exclude_workspace_id),
            category_slugs=category_slugs,
            platform=platform,
            min_followers=min_followers,
            max_followers=max_followers,
            min_engagement_rate=min_engagement_rate,
            country=country,
            city=city,
            languages=languages,
            max_monthly_retainer=max_monthly_retainer,
            availability=availability,
            verified_only=verified_only,
        )

        total = query.count()

        rows = (
            query.options(
                selectinload(CreatorProfile.social_accounts),
                selectinload(CreatorProfile.categories),
                selectinload(CreatorProfile.workspace),
            )
            .order_by(
                self._rank_expression(now).desc(),
                CreatorProfile.created_at.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        return rows, total

    def get_discoverable(
        self,
        profile_id: UUID,
    ) -> CreatorProfile | None:
        return (
            self._base_query(None)
            .options(
                selectinload(CreatorProfile.social_accounts),
                selectinload(CreatorProfile.portfolio_items),
                selectinload(CreatorProfile.rates),
                selectinload(CreatorProfile.categories),
                selectinload(CreatorProfile.workspace),
            )
            .filter(CreatorProfile.id == profile_id)
            .first()
        )
