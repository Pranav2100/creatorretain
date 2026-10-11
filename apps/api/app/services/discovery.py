from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.common.entitlements import Capability
from app.common.enums import CreatorAvailability, SocialPlatform
from app.common.exceptions import NotFoundError, PlanLimitError
from app.database.models.creator_profile import CreatorProfile
from app.database.repositories.discovery import DiscoveryRepository
from app.services.workspace_member import WorkspaceMemberService

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50

# Filters a Free plan cannot use. Category, platform, reach, country
# and availability stay open, so Free is usable rather than crippled -
# what it lacks is precision and the size of the result set.
ADVANCED_FILTERS = {
    "min_engagement_rate",
    "languages",
    "max_monthly_retainer",
    "city",
    "verified_only",
}


@dataclass(frozen=True)
class DiscoveryFilters:
    category_slugs: list[str] | None = None
    platform: SocialPlatform | None = None
    min_followers: int | None = None
    max_followers: int | None = None
    min_engagement_rate: Decimal | None = None
    country: str | None = None
    city: str | None = None
    languages: list[str] | None = None
    max_monthly_retainer: Decimal | None = None
    availability: CreatorAvailability | None = None
    verified_only: bool = False

    def advanced_in_use(self) -> list[str]:
        used = []

        for name in sorted(ADVANCED_FILTERS):
            value = getattr(self, name)

            if value is None or value is False:
                continue

            used.append(name)

        return used


@dataclass(frozen=True)
class DiscoveryResult:
    profiles: list[CreatorProfile]
    total_matching: int
    returned: int
    offset: int
    result_cap: int | None
    capped: bool
    can_contact: bool


class DiscoveryService:
    def __init__(
        self,
        repository: DiscoveryRepository,
        member_service: WorkspaceMemberService,
    ):
        self.repository = repository
        self.member_service = member_service

    def search(
        self,
        current_user_id: UUID,
        filters: DiscoveryFilters,
        offset: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> DiscoveryResult:
        context = self.member_service.resolve_context(current_user_id)
        context.require_capability(Capability.BROWSE_CREATORS)

        if not context.can(Capability.ADVANCED_FILTERS):
            used = filters.advanced_in_use()

            if used:
                raise PlanLimitError(
                    "Upgrade to Pro to filter by "
                    f"{self._readable(used)}."
                )

        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        offset = max(0, offset)

        cap = context.limits.discovery_results

        # A capped plan sees the first `cap` results of any search and
        # can run as many searches as it likes. total_matching is
        # reported whole, so the number they are not seeing is the
        # thing that argues for upgrading.
        if cap is not None:
            if offset >= cap:
                _, total = self.repository.search(
                    exclude_workspace_id=context.workspace_id,
                    offset=0,
                    limit=1,
                    **filters.__dict__,
                )

                return DiscoveryResult(
                    profiles=[],
                    total_matching=total,
                    returned=0,
                    offset=offset,
                    result_cap=cap,
                    capped=True,
                    can_contact=context.can(
                        Capability.CONTACT_CREATOR,
                    ),
                )

            page_size = min(page_size, cap - offset)

        profiles, total = self.repository.search(
            exclude_workspace_id=context.workspace_id,
            offset=offset,
            limit=page_size,
            **filters.__dict__,
        )

        return DiscoveryResult(
            profiles=profiles,
            total_matching=total,
            returned=len(profiles),
            offset=offset,
            result_cap=cap,
            capped=cap is not None and total > cap,
            can_contact=context.can(Capability.CONTACT_CREATOR),
        )

    def get_profile(
        self,
        current_user_id: UUID,
        profile_id: UUID,
    ) -> tuple[CreatorProfile, bool]:
        context = self.member_service.resolve_context(current_user_id)
        context.require_capability(Capability.VIEW_CREATOR_PROFILE)

        profile = self.repository.get_discoverable(profile_id)

        if profile is None:
            raise NotFoundError("Creator not found.")

        return profile, context.can(Capability.CONTACT_CREATOR)

    @staticmethod
    def _readable(names: list[str]) -> str:
        labels = {
            "min_engagement_rate": "engagement rate",
            "languages": "language",
            "max_monthly_retainer": "budget",
            "city": "city",
            "verified_only": "verified creators only",
        }

        readable = [labels.get(name, name) for name in names]

        if len(readable) == 1:
            return readable[0]

        return ", ".join(readable[:-1]) + f" and {readable[-1]}"
