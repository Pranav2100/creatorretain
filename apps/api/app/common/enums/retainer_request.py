from enum import Enum

from app.common.enums.retainer_status import RetainerStatus


class RetainerRequest(str, Enum):
    """
    A change one side has asked for and the other has not yet
    answered.

    Pausing stops the months accruing, which stops the money, so
    it is not one party's to do alone. Ending is deliberately not
    here: it serves notice instead, because a change that needs
    the other side's permission is a change they can refuse
    forever, and nobody should be locked into an agreement by
    someone declining to let them leave.
    """

    PAUSE = "pause"
    RESUME = "resume"

    @property
    def requires_status(self) -> RetainerStatus:
        """The status a retainer must be in for this to make sense."""
        return _REQUIRES[self]

    @property
    def resulting_status(self) -> RetainerStatus:
        return _RESULTS_IN[self]


_REQUIRES = {
    RetainerRequest.PAUSE: RetainerStatus.ACTIVE,
    RetainerRequest.RESUME: RetainerStatus.PAUSED,
}

_RESULTS_IN = {
    RetainerRequest.PAUSE: RetainerStatus.PAUSED,
    RetainerRequest.RESUME: RetainerStatus.ACTIVE,
}
