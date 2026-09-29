from enum import Enum


class WorkspacePlan(str, Enum):
    """
    Every plan across every workspace type.

    A single column holds this, and the capability map is keyed by
    (workspace_type, plan) - so "free" can mean different things to
    a brand and to a creator without needing a column per type.
    """

    # All workspace types
    FREE = "free"

    # Brand and agency
    PRO = "pro"
    BUSINESS = "business"

    # Brand only
    MANAGED = "managed"

    # Creator only
    VERIFIED = "verified"
