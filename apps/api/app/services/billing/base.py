from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.common.enums.subscription import SubscriptionStatus
from app.common.enums.workspace_plan import WorkspacePlan


@dataclass(frozen=True)
class Checkout:
    """
    What the person needs in order to start paying.

    The provider's id so renewals can be matched back, and a URL
    to send them to. Nothing in this application ever touches a
    card number: the person leaves, pays, and comes back, which
    is what keeps every card rule somebody else's problem.
    """

    subscription_id: str
    pay_url: str | None


@dataclass(frozen=True)
class BillingUpdate:
    """
    One thing a provider is telling us, in our words.

    Providers disagree about almost everything - Razorpay has a
    dozen subscription states and Stripe has a different dozen,
    with different names for the same thing. Translating at the
    boundary means the service above reads one vocabulary, and
    adding a second provider is a translation rather than a
    branch in the business logic.

    `paid_until` is the only field that really matters. It is
    what gets written onto the workspace, and what the whole
    application reads to decide whether somebody is a customer.
    """

    event_id: str
    kind: str
    subscription_id: str
    status: SubscriptionStatus | None = None
    paid_until: datetime | None = None
    amount: int | None = None


class BillingProvider(ABC):
    """
    Anything that can take money for a plan.

    The same shape as EmailSender, for the same reason: the one
    real provider is going to be joined by a second, because
    Razorpay is right for India and wrong internationally, and
    neither the service nor the routes should have to know which
    one is behind this.
    """

    #: Written onto every subscription row, so an old row is
    #: never mistaken for one belonging to a different provider.
    name: str = "unnamed"

    @abstractmethod
    def start(
        self,
        *,
        plan: WorkspacePlan,
        workspace_id: str,
        email: str,
        name: str,
    ) -> Checkout:
        """Begin a subscription and return where to send them."""

    @abstractmethod
    def cancel(
        self,
        subscription_id: str,
        *,
        at_period_end: bool = True,
    ) -> None:
        """
        Stop it renewing.

        Defaults to the end of the period, because somebody who
        cancels on the third of the month has already paid for
        that month and should keep it.
        """

    @abstractmethod
    def verify(self, body: bytes, signature: str) -> bool:
        """
        Whether this webhook really came from the provider.

        Anybody can POST to a webhook URL. Without this, a
        stranger can grant themselves a plan by describing one.
        """

    @abstractmethod
    def read(self, payload: dict) -> BillingUpdate | None:
        """
        Translate a verified webhook into our vocabulary.

        None for events we do not act on, which is most of them.
        """
