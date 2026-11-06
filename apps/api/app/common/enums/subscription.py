from enum import Enum


class SubscriptionStatus(str, Enum):
    """
    Where a subscription is with the provider.

    Deliberately a small set. Razorpay alone has a dozen states
    and Stripe has a different dozen; mapping both onto these
    five is the provider's job, so nothing above the provider
    layer has to know whose vocabulary it is reading.

    The only distinction that really matters to the application
    is whether the workspace is currently paid for, and that is
    not read from here at all - it is read from the workspace's
    plan_expires_at, which this keeps pushed forward. A
    subscription that stops renewing needs no sweeping: the date
    simply stops moving and the plan lapses on its own.
    """

    # Created, not yet paid. The person has been sent to the
    # provider and has not finished, or the first charge has not
    # cleared.
    PENDING = "pending"

    # Paying. The usual state.
    ACTIVE = "active"

    # The provider is retrying a failed charge. Still a customer,
    # for now - their plan_expires_at carries them to the end of
    # what they paid for and no further.
    PAST_DUE = "past_due"

    # Will not renew, but still paid up until the date. Somebody
    # who cancels on the 3rd keeps what they bought until the
    # month is out.
    CANCELLING = "cancelling"

    # Over. Either cancelled and lapsed, or abandoned before the
    # first payment.
    ENDED = "ended"

    @property
    def is_live(self) -> bool:
        """
        Whether this subscription is one the workspace still has.

        Includes CANCELLING, which is the point: cancelling is a
        decision about the next renewal, not a refund of the one
        already paid for.
        """
        return self in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.CANCELLING,
        )
