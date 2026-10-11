from enum import Enum


class RetainerStatus(str, Enum):
    """
    The life of an agreement.

    PENDING is an offer the brand has sent and the creator has not
    answered. Only PENDING and ACTIVE count against the plan's
    retainer limit - otherwise a workspace at its ceiling could
    send unlimited offers and simply wait for one to be accepted.
    """

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    ENDED = "ended"


# Statuses that occupy a slot in the workspace's plan allowance.
OCCUPYING_STATUSES = (
    RetainerStatus.PENDING,
    RetainerStatus.ACTIVE,
)

# Statuses past which nothing more happens. A retainer in one of
# these never grows another period.
TERMINAL_STATUSES = (
    RetainerStatus.DECLINED,
    RetainerStatus.CANCELLED,
    RetainerStatus.ENDED,
)
