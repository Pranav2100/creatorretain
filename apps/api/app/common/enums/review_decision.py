from enum import Enum

from app.common.enums.deliverable_status import DeliverableStatus


class ReviewDecision(str, Enum):
    """
    The three answers a brand can give to submitted work.

    Separate from DeliverableStatus so the request schema offers
    only valid choices. Reusing the status enum meant the API
    advertised five options and refused two of them at runtime,
    which reads as a bug to anyone working from the docs.
    """

    APPROVE = "approve"
    REQUEST_REVISION = "request_revision"
    REJECT = "reject"

    def to_status(self) -> DeliverableStatus:
        return _RESULTING_STATUS[self]


_RESULTING_STATUS: dict[ReviewDecision, DeliverableStatus] = {
    ReviewDecision.APPROVE: DeliverableStatus.APPROVED,
    ReviewDecision.REQUEST_REVISION: (
        DeliverableStatus.REVISION_REQUESTED
    ),
    ReviewDecision.REJECT: DeliverableStatus.REJECTED,
}
