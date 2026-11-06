import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

from app.common.enums.subscription import SubscriptionStatus
from app.common.enums.workspace_plan import WorkspacePlan
from app.services.billing.base import (
    BillingProvider,
    BillingUpdate,
    Checkout,
)

# The secret the fake signs with. Not a secret, obviously - the
# point is that the signature check is exercised by the suites
# rather than skipped, so a forged webhook is refused in tests
# the same way it would be in production.
FAKE_SECRET = b"fake-billing-secret"


class FakeBillingProvider(BillingProvider):
    """
    A provider that takes no money.

    The default, and what every test runs against. Billing is the
    one part of an application that cannot be exercised honestly
    against the real thing - you cannot charge a card in a test
    suite, and a provider's sandbox needs network, credentials
    and somebody's account.

    So this behaves like a provider: it issues ids, it signs its
    webhooks and checks the signature, and it refuses a forged
    one. Everything above it - matching a renewal to a
    workspace, refusing a replay, pushing the paid-until date -
    is the same code that will run against Razorpay.
    """

    name = "fake"

    def __init__(self):
        self.started: list[dict] = []
        self.cancelled: list[str] = []

    def start(
        self,
        *,
        plan: WorkspacePlan,
        workspace_id: str,
        email: str,
        name: str,
    ) -> Checkout:
        subscription_id = f"fake_sub_{uuid.uuid4().hex[:16]}"

        self.started.append(
            {
                "subscription_id": subscription_id,
                "plan": plan.value,
                "workspace_id": workspace_id,
                "email": email,
                "name": name,
            }
        )

        return Checkout(
            subscription_id=subscription_id,
            pay_url=f"https://example.invalid/pay/{subscription_id}",
        )

    def cancel(
        self,
        subscription_id: str,
        *,
        at_period_end: bool = True,
    ) -> None:
        self.cancelled.append(subscription_id)

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    @staticmethod
    def sign(body: bytes) -> str:
        return hmac.new(
            FAKE_SECRET, body, hashlib.sha256
        ).hexdigest()

    def verify(self, body: bytes, signature: str) -> bool:
        # compare_digest rather than ==, for the same reason the
        # real one does it: == on secrets leaks their contents
        # through how long it takes to fail.
        return hmac.compare_digest(self.sign(body), signature or "")

    def read(self, payload: dict) -> BillingUpdate | None:
        kind = payload.get("event")

        known = {
            "subscription.activated": SubscriptionStatus.ACTIVE,
            "subscription.charged": SubscriptionStatus.ACTIVE,
            "subscription.pending": SubscriptionStatus.PAST_DUE,
            "subscription.halted": SubscriptionStatus.PAST_DUE,
            "subscription.cancelled": SubscriptionStatus.CANCELLING,
            "subscription.completed": SubscriptionStatus.ENDED,
        }

        if kind not in known:
            return None

        paid_until = payload.get("paid_until")

        return BillingUpdate(
            event_id=payload.get("id", ""),
            kind=kind,
            subscription_id=payload.get("subscription_id", ""),
            status=known[kind],
            paid_until=(
                datetime.fromisoformat(paid_until)
                if paid_until
                else None
            ),
            amount=payload.get("amount"),
        )

    # ------------------------------------------------------------------
    # Only for tests: build an event the way a provider would
    # ------------------------------------------------------------------

    @staticmethod
    def event(
        kind: str,
        subscription_id: str,
        *,
        event_id: str | None = None,
        days: int = 30,
        amount: int | None = None,
    ) -> tuple[bytes, str]:
        """
        A signed webhook body, as the provider would send it.

        Returns the bytes and the signature, because a suite has
        to post exactly the bytes that were signed - re-encoding
        the JSON in between is itself a way to break signature
        verification, and a test that re-encodes would pass
        while production failed.
        """
        payload = {
            "id": event_id or f"evt_{uuid.uuid4().hex[:16]}",
            "event": kind,
            "subscription_id": subscription_id,
            "paid_until": (
                datetime.now(UTC) + timedelta(days=days)
            ).isoformat(),
        }

        if amount is not None:
            payload["amount"] = amount

        body = json.dumps(payload).encode()

        return body, FakeBillingProvider.sign(body)
