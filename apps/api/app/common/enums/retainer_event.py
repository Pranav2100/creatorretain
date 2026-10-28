from enum import Enum


class RetainerEventKind(str, Enum):
    """
    Something that happened to a retainer, kept forever.

    One row per thing a person did, not per field that changed.
    Agreeing to a pause is one event, even though it moves a
    status, clears a request and stamps a time, because that is
    how the two people involved would describe it afterwards.

    Nothing here is derived. The rest of this project works out
    the present from stored facts - a plan that reads as Free once
    it lapses, a retainer that reads as ended once its notice runs
    out - but the past cannot be recomputed from the present, and
    a disagreement about who paused what in March is settled by a
    record or it is not settled at all.
    """

    # Before it starts
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    OFFER_WITHDRAWN = "offer_withdrawn"

    # Pausing, which both sides have to want
    PAUSE_REQUESTED = "pause_requested"
    RESUME_REQUESTED = "resume_requested"
    REQUEST_REJECTED = "request_rejected"
    REQUEST_WITHDRAWN = "request_withdrawn"
    PAUSED = "paused"
    RESUMED = "resumed"

    # Leaving
    NOTICE_GIVEN = "notice_given"
    ENDED = "ended"

    # The work itself
    WORK_SUBMITTED = "work_submitted"
    WORK_APPROVED = "work_approved"
    CHANGES_REQUESTED = "changes_requested"
    WORK_REJECTED = "work_rejected"

    @property
    def is_about_work(self) -> bool:
        """
        Whether this is one deliverable rather than the agreement.

        A month of four reels can produce a dozen of these against
        a handful of the others, so a reader usually wants them
        separable.
        """
        return self in _ABOUT_WORK


_ABOUT_WORK = frozenset(
    {
        RetainerEventKind.WORK_SUBMITTED,
        RetainerEventKind.WORK_APPROVED,
        RetainerEventKind.CHANGES_REQUESTED,
        RetainerEventKind.WORK_REJECTED,
    }
)
