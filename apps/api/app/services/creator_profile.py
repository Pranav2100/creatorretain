from decimal import Decimal
from uuid import UUID

from app.common.enums import (
    CreatorProfileStatus,
    WorkspaceType,
)
from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.database.models.content_category import ContentCategory
from app.database.models.creator_portfolio_item import (
    CreatorPortfolioItem,
)
from app.database.models.creator_profile import CreatorProfile
from app.database.models.creator_rate import CreatorRate
from app.database.models.creator_social_account import (
    CreatorSocialAccount,
)
from app.database.repositories.creator_profile import (
    CreatorProfileRepository,
)
from app.services.workspace_member import WorkspaceMemberService

MAX_CATEGORIES = 5

# Weights sum to 100. Everything except portfolio is required for
# a profile to go live, so a published profile always scores 95+.
COMPLETENESS_WEIGHTS = {
    "headline": 10,
    "bio": 15,
    "location": 10,
    "languages": 5,
    "categories": 15,
    "social": 25,
    "pricing": 15,
    "portfolio": 5,
}

REQUIRED_FIELDS = (
    "headline",
    "bio",
    "location",
    "languages",
    "categories",
    "social",
    "pricing",
)


class CreatorProfileService:
    def __init__(
        self,
        repository: CreatorProfileRepository,
        member_service: WorkspaceMemberService,
    ):
        self.repository = repository
        self.member_service = member_service

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def _creator_workspace(self, current_user_id: UUID):
        context = self.member_service.resolve_context(current_user_id)

        if context.workspace.workspace_type != WorkspaceType.CREATOR:
            raise PermissionDeniedError(
                "Only creator workspaces have a creator profile."
            )

        return context.workspace

    def get_or_create(self, current_user_id: UUID) -> CreatorProfile:
        workspace = self._creator_workspace(current_user_id)

        profile = self.repository.get_by_workspace(workspace.id)

        if profile is not None:
            return profile

        profile = CreatorProfile(
            workspace_id=workspace.id,
            languages=[],
            skills=[],
        )

        return self.repository.create(profile)

    def _profile(self, current_user_id: UUID) -> CreatorProfile:
        return self.get_or_create(current_user_id)

    # ------------------------------------------------------------------
    # Basics
    # ------------------------------------------------------------------

    def update_basics(
        self,
        current_user_id: UUID,
        **fields,
    ) -> CreatorProfile:
        profile = self._profile(current_user_id)

        for key, value in fields.items():
            if value is None:
                continue

            setattr(profile, key, value)

        return self._recalculate(profile)

    def set_categories(
        self,
        current_user_id: UUID,
        category_ids: list[UUID],
    ) -> CreatorProfile:
        if len(category_ids) > MAX_CATEGORIES:
            raise ConflictError(
                f"Choose at most {MAX_CATEGORIES} categories."
            )

        profile = self._profile(current_user_id)

        categories = self.repository.get_categories_by_ids(
            category_ids,
        )

        if len(categories) != len(set(category_ids)):
            raise NotFoundError("One or more categories not found.")

        profile.categories = categories

        return self._recalculate(profile)

    def set_visibility(
        self,
        current_user_id: UUID,
        is_hidden: bool,
    ) -> CreatorProfile:
        """
        The system decides whether a profile is ready. The creator
        decides whether it is visible.
        """
        profile = self._profile(current_user_id)
        profile.is_hidden = is_hidden

        return self.repository.save(profile)

    # ------------------------------------------------------------------
    # Social accounts
    # ------------------------------------------------------------------

    def add_social_account(
        self,
        current_user_id: UUID,
        platform,
        handle: str,
        profile_url: str | None = None,
        claimed_followers: int | None = None,
        claimed_engagement_rate: Decimal | None = None,
    ) -> CreatorSocialAccount:
        profile = self._profile(current_user_id)

        existing = self.repository.get_social_account_by_platform(
            profile.id,
            platform,
        )

        if existing is not None:
            raise ConflictError(
                f"A {platform.value} account is already linked. "
                "Edit it instead."
            )

        account = CreatorSocialAccount(
            profile_id=profile.id,
            platform=platform,
            handle=handle.strip().lstrip("@"),
            profile_url=profile_url,
            claimed_followers=claimed_followers,
            claimed_engagement_rate=claimed_engagement_rate,
        )

        self.repository.db.add(account)
        self.repository.db.flush()
        self.repository.db.refresh(profile)
        self._recalculate(profile)

        return account

    def update_social_account(
        self,
        current_user_id: UUID,
        account_id: UUID,
        **fields,
    ) -> CreatorSocialAccount:
        profile = self._profile(current_user_id)
        account = self._owned_social_account(profile, account_id)

        for key, value in fields.items():
            if value is None:
                continue

            if key == "handle":
                value = value.strip().lstrip("@")

            setattr(account, key, value)

        self.repository.db.flush()
        self._recalculate(profile)

        return account

    def remove_social_account(
        self,
        current_user_id: UUID,
        account_id: UUID,
    ) -> None:
        profile = self._profile(current_user_id)
        account = self._owned_social_account(profile, account_id)

        self.repository.db.delete(account)
        self.repository.db.flush()
        self.repository.db.refresh(profile)
        self._recalculate(profile)

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def add_portfolio_item(
        self,
        current_user_id: UUID,
        title: str,
        description: str | None = None,
        platform=None,
        external_url: str | None = None,
        media_url: str | None = None,
    ) -> CreatorPortfolioItem:
        profile = self._profile(current_user_id)

        item = CreatorPortfolioItem(
            profile_id=profile.id,
            title=title,
            description=description,
            platform=platform,
            external_url=external_url,
            media_url=media_url,
            position=self.repository.next_portfolio_position(
                profile.id,
            ),
        )

        self.repository.db.add(item)
        self.repository.db.flush()
        self.repository.db.refresh(profile)
        self._recalculate(profile)

        return item

    def update_portfolio_item(
        self,
        current_user_id: UUID,
        item_id: UUID,
        **fields,
    ) -> CreatorPortfolioItem:
        profile = self._profile(current_user_id)
        item = self._owned_portfolio_item(profile, item_id)

        for key, value in fields.items():
            if value is None:
                continue

            setattr(item, key, value)

        self.repository.commit()

        return item

    def remove_portfolio_item(
        self,
        current_user_id: UUID,
        item_id: UUID,
    ) -> None:
        profile = self._profile(current_user_id)
        item = self._owned_portfolio_item(profile, item_id)

        self.repository.db.delete(item)
        self.repository.db.flush()
        self.repository.db.refresh(profile)
        self._recalculate(profile)

    # ------------------------------------------------------------------
    # Rates
    # ------------------------------------------------------------------

    def add_rate(
        self,
        current_user_id: UUID,
        deliverable_type,
        price: Decimal,
        quantity: int = 1,
        currency: str = "INR",
        notes: str | None = None,
    ) -> CreatorRate:
        profile = self._profile(current_user_id)

        if price <= 0:
            raise ConflictError("A rate must be more than zero.")

        rate = CreatorRate(
            profile_id=profile.id,
            deliverable_type=deliverable_type,
            price=price,
            quantity=quantity,
            currency=currency.upper(),
            notes=notes,
        )

        self.repository.db.add(rate)
        self.repository.db.flush()
        self.repository.db.refresh(profile)
        self._recalculate(profile)

        return rate

    def update_rate(
        self,
        current_user_id: UUID,
        rate_id: UUID,
        **fields,
    ) -> CreatorRate:
        profile = self._profile(current_user_id)
        rate = self._owned_rate(profile, rate_id)

        for key, value in fields.items():
            if value is None:
                continue

            if key == "price" and value <= 0:
                raise ConflictError("A rate must be more than zero.")

            if key == "currency":
                value = value.upper()

            setattr(rate, key, value)

        self.repository.commit()

        return rate

    def remove_rate(
        self,
        current_user_id: UUID,
        rate_id: UUID,
    ) -> None:
        profile = self._profile(current_user_id)
        rate = self._owned_rate(profile, rate_id)

        self.repository.db.delete(rate)
        self.repository.db.flush()
        self.repository.db.refresh(profile)
        self._recalculate(profile)

    # ------------------------------------------------------------------
    # Categories reference data
    # ------------------------------------------------------------------

    def list_categories(self) -> list[ContentCategory]:
        return self.repository.list_categories()

    # ------------------------------------------------------------------
    # Completeness
    # ------------------------------------------------------------------

    def _checks(self, profile: CreatorProfile) -> dict[str, bool]:
        has_social = any(
            account.followers is not None
            for account in profile.social_accounts
        )

        has_pricing = (
            profile.monthly_retainer_min is not None
            or len(profile.rates) > 0
        )

        return {
            "headline": bool(profile.headline),
            "bio": bool(profile.bio),
            "location": bool(profile.city and profile.country),
            "languages": len(profile.languages or []) > 0,
            "categories": len(profile.categories) > 0,
            "social": has_social,
            "pricing": has_pricing,
            "portfolio": len(profile.portfolio_items) > 0,
        }

    def missing_fields(self, profile: CreatorProfile) -> list[str]:
        checks = self._checks(profile)

        return [
            field for field in REQUIRED_FIELDS if not checks[field]
        ]

    def _recalculate(
        self,
        profile: CreatorProfile,
    ) -> CreatorProfile:
        """
        Score the profile and publish it when everything required is
        present. Publishing is derived rather than a button, so a
        finished profile is discoverable without another step.
        """
        checks = self._checks(profile)

        profile.completeness = sum(
            weight
            for field, weight in COMPLETENESS_WEIGHTS.items()
            if checks[field]
        )

        if profile.status != CreatorProfileStatus.SUSPENDED:
            complete = all(
                checks[field] for field in REQUIRED_FIELDS
            )

            profile.status = (
                CreatorProfileStatus.PUBLISHED
                if complete
                else CreatorProfileStatus.DRAFT
            )

        return self.repository.save(profile)

    # ------------------------------------------------------------------
    # Ownership guards
    # ------------------------------------------------------------------

    def _owned_social_account(self, profile, account_id):
        account = self.repository.get_social_account(account_id)

        if account is None or account.profile_id != profile.id:
            raise NotFoundError("Social account not found.")

        return account

    def _owned_portfolio_item(self, profile, item_id):
        item = self.repository.get_portfolio_item(item_id)

        if item is None or item.profile_id != profile.id:
            raise NotFoundError("Portfolio item not found.")

        return item

    def _owned_rate(self, profile, rate_id):
        rate = self.repository.get_rate(rate_id)

        if rate is None or rate.profile_id != profile.id:
            raise NotFoundError("Rate not found.")

        return rate
