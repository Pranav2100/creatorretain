from dataclasses import dataclass
from enum import StrEnum

from app.common.enums import WorkspacePlan, WorkspaceType


class Capability(StrEnum):
    """
    Something a workspace is allowed to do because of its plan.

    Distinct from WorkspacePermission, which is about the role a
    person holds inside a workspace. A Free-plan owner has every
    permission and few capabilities; a Business-plan member has
    every capability and few permissions. Both checks apply.
    """

    # Discovery
    BROWSE_CREATORS = "browse_creators"
    VIEW_CREATOR_PROFILE = "view_creator_profile"
    ADVANCED_FILTERS = "advanced_filters"

    # Hiring
    CONTACT_CREATOR = "contact_creator"
    CREATE_RETAINER = "create_retainer"
    CREATE_CAMPAIGN = "create_campaign"
    CAMPAIGN_DASHBOARD = "campaign_dashboard"

    # Service
    MANAGED_SERVICE = "managed_service"

    # Creator
    PUBLISH_PROFILE = "publish_profile"
    RECEIVE_OFFERS = "receive_offers"
    VERIFIED_BADGE = "verified_badge"

    # Agency
    REPRESENT_CREATORS = "represent_creators"


@dataclass(frozen=True)
class PlanLimits:
    """
    Numeric ceilings. None means no ceiling.

    Kept beside the capability sets so a tier is described in one
    place: what it can do, and how much of it.
    """

    # Results a single discovery search returns. None means no cap.
    #
    # Free is capped, so the catalogue itself is the thing a paid
    # plan buys. CONTACT_CREATOR gates reaching out on top of that,
    # which means Free is held back twice: it sees a slice, and
    # cannot message even that slice.
    discovery_results: int | None = None

    # Retainers a workspace may have running at once.
    active_retainers: int | None = None

    # Creators an agency may represent.
    represented_creators: int | None = None

    # People in the workspace, including the owner.
    team_members: int | None = None


UNLIMITED = PlanLimits()


BRAND_FREE = frozenset(
    {
        Capability.BROWSE_CREATORS,
        Capability.VIEW_CREATOR_PROFILE,
    }
)

BRAND_PRO = BRAND_FREE | {
    Capability.ADVANCED_FILTERS,
    Capability.CONTACT_CREATOR,
    Capability.CREATE_RETAINER,
    Capability.CREATE_CAMPAIGN,
}

BRAND_BUSINESS = BRAND_PRO | {Capability.CAMPAIGN_DASHBOARD}

BRAND_MANAGED = BRAND_BUSINESS | {Capability.MANAGED_SERVICE}


CREATOR_FREE = frozenset(
    {
        Capability.PUBLISH_PROFILE,
        Capability.RECEIVE_OFFERS,
    }
)

CREATOR_VERIFIED = CREATOR_FREE | {Capability.VERIFIED_BADGE}


AGENCY_FREE = frozenset(
    {
        Capability.BROWSE_CREATORS,
        Capability.VIEW_CREATOR_PROFILE,
        Capability.REPRESENT_CREATORS,
    }
)

AGENCY_PRO = AGENCY_FREE | {
    Capability.ADVANCED_FILTERS,
    Capability.CONTACT_CREATOR,
    Capability.CREATE_RETAINER,
    Capability.CREATE_CAMPAIGN,
}

AGENCY_BUSINESS = AGENCY_PRO | {Capability.CAMPAIGN_DASHBOARD}


PLAN_CAPABILITIES: dict[
    tuple[WorkspaceType, WorkspacePlan], frozenset[Capability]
] = {
    (WorkspaceType.BRAND, WorkspacePlan.FREE): BRAND_FREE,
    (WorkspaceType.BRAND, WorkspacePlan.PRO): BRAND_PRO,
    (WorkspaceType.BRAND, WorkspacePlan.BUSINESS): BRAND_BUSINESS,
    (WorkspaceType.BRAND, WorkspacePlan.MANAGED): BRAND_MANAGED,
    (WorkspaceType.CREATOR, WorkspacePlan.FREE): CREATOR_FREE,
    (WorkspaceType.CREATOR, WorkspacePlan.VERIFIED): CREATOR_VERIFIED,
    (WorkspaceType.AGENCY, WorkspacePlan.FREE): AGENCY_FREE,
    (WorkspaceType.AGENCY, WorkspacePlan.PRO): AGENCY_PRO,
    (WorkspaceType.AGENCY, WorkspacePlan.BUSINESS): AGENCY_BUSINESS,
}


# Gate what earns revenue - retainers, contact, represented
# creators - and stay generous on what merely helps a workspace use
# the product. A team that cannot add a colleague churns before it
# ever reaches the paywall that matters.
PLAN_LIMITS: dict[tuple[WorkspaceType, WorkspacePlan], PlanLimits] = {
    (WorkspaceType.BRAND, WorkspacePlan.FREE): PlanLimits(
        discovery_results=10,
        active_retainers=0,
        team_members=10,
    ),
    (WorkspaceType.BRAND, WorkspacePlan.PRO): PlanLimits(
        active_retainers=3,
        team_members=25,
    ),
    (WorkspaceType.BRAND, WorkspacePlan.BUSINESS): UNLIMITED,
    (WorkspaceType.BRAND, WorkspacePlan.MANAGED): UNLIMITED,
    (WorkspaceType.CREATOR, WorkspacePlan.FREE): PlanLimits(
        team_members=1,
    ),
    (WorkspaceType.CREATOR, WorkspacePlan.VERIFIED): PlanLimits(
        team_members=1,
    ),
    (WorkspaceType.AGENCY, WorkspacePlan.FREE): PlanLimits(
        discovery_results=10,
        active_retainers=0,
        represented_creators=3,
        team_members=10,
    ),
    (WorkspaceType.AGENCY, WorkspacePlan.PRO): PlanLimits(
        active_retainers=10,
        represented_creators=25,
        team_members=25,
    ),
    (WorkspaceType.AGENCY, WorkspacePlan.BUSINESS): UNLIMITED,
}


# What a workspace of each type is allowed to be on. Anything else
# is a configuration mistake: a creator cannot be on Business.
PLANS_BY_TYPE: dict[WorkspaceType, tuple[WorkspacePlan, ...]] = {
    WorkspaceType.BRAND: (
        WorkspacePlan.FREE,
        WorkspacePlan.PRO,
        WorkspacePlan.BUSINESS,
        WorkspacePlan.MANAGED,
    ),
    WorkspaceType.CREATOR: (
        WorkspacePlan.FREE,
        WorkspacePlan.VERIFIED,
    ),
    WorkspaceType.AGENCY: (
        WorkspacePlan.FREE,
        WorkspacePlan.PRO,
        WorkspacePlan.BUSINESS,
    ),
}


# Shown when a capability is missing, so the error tells the person
# what to do rather than only that they cannot do it.
UPGRADE_HINTS: dict[Capability, str] = {
    Capability.ADVANCED_FILTERS: "Pro",
    Capability.CONTACT_CREATOR: "Pro",
    Capability.CREATE_RETAINER: "Pro",
    Capability.CREATE_CAMPAIGN: "Pro",
    Capability.CAMPAIGN_DASHBOARD: "Business",
    Capability.MANAGED_SERVICE: "Managed",
    Capability.VERIFIED_BADGE: "Verified",
}


def plans_for_type(
    workspace_type: WorkspaceType,
) -> tuple[WorkspacePlan, ...]:
    return PLANS_BY_TYPE.get(workspace_type, (WorkspacePlan.FREE,))


def is_plan_valid(
    workspace_type: WorkspaceType,
    plan: WorkspacePlan,
) -> bool:
    return plan in plans_for_type(workspace_type)


def capabilities_for(
    workspace_type: WorkspaceType,
    plan: WorkspacePlan,
) -> frozenset[Capability]:
    """
    Falls back to the type's Free set rather than raising, so a
    workspace left on a plan that was later withdrawn keeps working
    at the lowest tier instead of erroring on every request.
    """
    capabilities = PLAN_CAPABILITIES.get((workspace_type, plan))

    if capabilities is not None:
        return capabilities

    return PLAN_CAPABILITIES.get(
        (workspace_type, WorkspacePlan.FREE),
        frozenset(),
    )


def limits_for(
    workspace_type: WorkspaceType,
    plan: WorkspacePlan,
) -> PlanLimits:
    limits = PLAN_LIMITS.get((workspace_type, plan))

    if limits is not None:
        return limits

    return PLAN_LIMITS.get(
        (workspace_type, WorkspacePlan.FREE),
        UNLIMITED,
    )


def has_capability(
    workspace_type: WorkspaceType,
    plan: WorkspacePlan,
    capability: Capability,
) -> bool:
    return capability in capabilities_for(workspace_type, plan)


def upgrade_message(capability: Capability) -> str:
    tier = UPGRADE_HINTS.get(capability)

    if tier is None:
        return "Your current plan does not include this."

    return f"Upgrade to {tier} to use this."
