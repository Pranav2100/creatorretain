from enum import Enum


class DeliverableStatus(str, Enum):
    """
    One unit of work inside a period.

    REVISION_REQUESTED is deliberately not a dead end: the creator
    submits again and it returns to SUBMITTED, which is how revisions
    actually work. REJECTED exists for the case where the brand is
    done asking.
    """

    PENDING = "pending"
    SUBMITTED = "submitted"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    REJECTED = "rejected"


# What the creator still owes. Used to decide whether a period is
# finished without storing a second copy of that fact.
OUTSTANDING_STATUSES = (
    DeliverableStatus.PENDING,
    DeliverableStatus.SUBMITTED,
    DeliverableStatus.REVISION_REQUESTED,
)
