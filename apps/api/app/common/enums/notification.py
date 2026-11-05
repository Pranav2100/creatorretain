from enum import Enum


class NotificationCategory(str, Enum):
    """
    The four switches a person gets.

    Grouped by what somebody would want to turn off, not by which
    service raises it - nobody thinks "I would like fewer events
    from the conversation service", they think "stop emailing me
    about messages".
    """

    RETAINERS = "retainers"
    MESSAGES = "messages"
    WORK = "work"
    SECURITY = "security"


class NotificationKind(str, Enum):
    """
    Every email the application can send, and nothing else.

    Deliberately not the same list as RetainerEventKind. That one
    records everything that happens to a retainer, including
    things nobody needs an email about - a withdrawn offer
    matters to the history and not to anybody's inbox. The
    mapping between the two lives in the notification service,
    and events with no entry simply do not notify.
    """

    # Money and decisions.
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"

    # Something is waiting on you.
    PAUSE_REQUESTED = "pause_requested"
    RESUME_REQUESTED = "resume_requested"
    REQUEST_REJECTED = "request_rejected"
    PAUSED = "paused"
    RESUMED = "resumed"
    NOTICE_GIVEN = "notice_given"
    ENDED = "ended"

    # Work review.
    WORK_SUBMITTED = "work_submitted"
    WORK_APPROVED = "work_approved"
    CHANGES_REQUESTED = "changes_requested"
    WORK_REJECTED = "work_rejected"

    # Conversations.
    UNREAD_MESSAGES = "unread_messages"
    MESSAGE_REQUEST = "message_request"

    # The account itself.
    PASSWORD_CHANGED = "password_changed"

    @property
    def category(self) -> NotificationCategory:
        return _CATEGORY[self]

    @property
    def is_security(self) -> bool:
        """
        Security mail is sent whatever the preferences say.

        Being told your password changed is not a newsletter. If
        it was not you, an email you cannot turn off is the whole
        point of it.
        """
        return self.category == NotificationCategory.SECURITY


_CATEGORY: dict[NotificationKind, NotificationCategory] = {
    NotificationKind.OFFER_RECEIVED: NotificationCategory.RETAINERS,
    NotificationKind.OFFER_ACCEPTED: NotificationCategory.RETAINERS,
    NotificationKind.OFFER_DECLINED: NotificationCategory.RETAINERS,
    NotificationKind.PAUSE_REQUESTED: NotificationCategory.RETAINERS,
    NotificationKind.RESUME_REQUESTED: NotificationCategory.RETAINERS,
    NotificationKind.REQUEST_REJECTED: NotificationCategory.RETAINERS,
    NotificationKind.PAUSED: NotificationCategory.RETAINERS,
    NotificationKind.RESUMED: NotificationCategory.RETAINERS,
    NotificationKind.NOTICE_GIVEN: NotificationCategory.RETAINERS,
    NotificationKind.ENDED: NotificationCategory.RETAINERS,
    NotificationKind.WORK_SUBMITTED: NotificationCategory.WORK,
    NotificationKind.WORK_APPROVED: NotificationCategory.WORK,
    NotificationKind.CHANGES_REQUESTED: NotificationCategory.WORK,
    NotificationKind.WORK_REJECTED: NotificationCategory.WORK,
    NotificationKind.UNREAD_MESSAGES: NotificationCategory.MESSAGES,
    NotificationKind.MESSAGE_REQUEST: NotificationCategory.MESSAGES,
    NotificationKind.PASSWORD_CHANGED: NotificationCategory.SECURITY,
}
