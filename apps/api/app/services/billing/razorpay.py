import hashlib
import hmac
from datetime import UTC, datetime

import httpx

from app.common.enums.subscription import SubscriptionStatus
from app.common.enums.workspace_plan import WorkspacePlan
from app.core.settings import settings
from app.services.billing.base import (
    BillingProvider,
    BillingUpdate,
    Checkout,
)

API = "https://api.razorpay.com/v1"

# How Razorpay's subscription states map onto ours. Theirs is the
# longer list; several of them mean the same thing to us.
#
# `halted` is worth knowing about: it is what Razorpay says after
# it has given up retrying a failed charge. We keep it as PAST_DUE
# rather than ENDED, because the workspace is still paid up until
# the date it already bought - letting that date pass is what
# ends the plan, not us deciding here that it has.
STATES: dict[str, SubscriptionStatus] = {
    "subscription.authenticated": SubscriptionStatus.PENDING,
    "subscription.activated": SubscriptionStatus.ACTIVE,
    "subscription.charged": SubscriptionStatus.ACTIVE,
    "subscription.pending": SubscriptionStatus.PAST_DUE,
    "subscription.halted": SubscriptionStatus.PAST_DUE,
    "subscription.cancelled": SubscriptionStatus.CANCELLING,
    "subscription.completed": SubscriptionStatus.ENDED,
    "subscription.expired": SubscriptionStatus.ENDED,
}


class RazorpayBillingProvider(BillingProvider):
    """
    Razorpay subscriptions.

    Chosen first because the money is in rupees and the first
    customers are Indian: UPI AutoPay is native here, the
    domestic rate is lower, and India's e-mandate rules are
    handled by Razorpay rather than by us. Stripe is the
    companion for international customers, and goes behind the
    same interface.

    Plans are created in Razorpay, not here - their plan_id is
    configured per plan. That is their model: a subscription is
    an instance of a plan that already exists on their side.
    """

    name = "razorpay"

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
    ):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = (
            webhook_secret or settings.RAZORPAY_WEBHOOK_SECRET
        )

    def _plan_id(self, plan: WorkspacePlan) -> str:
        mapping = {
            WorkspacePlan.PRO: settings.RAZORPAY_PLAN_PRO,
            WorkspacePlan.BUSINESS: settings.RAZORPAY_PLAN_BUSINESS,
        }

        plan_id = mapping.get(plan)

        if not plan_id:
            raise ValueError(
                f"No Razorpay plan is configured for {plan.value}."
            )

        return plan_id

    def start(
        self,
        *,
        plan: WorkspacePlan,
        workspace_id: str,
        email: str,
        name: str,
    ) -> Checkout:
        response = httpx.post(
            f"{API}/subscriptions",
            auth=(self.key_id, self.key_secret),
            json={
                "plan_id": self._plan_id(plan),
                # Open-ended in practice. Razorpay wants a count;
                # ten years of months is the usual way to say
                # "until they cancel".
                "total_count": 120,
                "customer_notify": 1,
                # Carried back on every webhook, which is how a
                # renewal two years from now is matched to a
                # workspace without trusting anything the caller
                # sends us.
                "notes": {
                    "workspace_id": workspace_id,
                    "plan": plan.value,
                },
            },
            timeout=20,
        )

        response.raise_for_status()
        body = response.json()

        return Checkout(
            subscription_id=body["id"],
            pay_url=body.get("short_url"),
        )

    def cancel(
        self,
        subscription_id: str,
        *,
        at_period_end: bool = True,
    ) -> None:
        response = httpx.post(
            f"{API}/subscriptions/{subscription_id}/cancel",
            auth=(self.key_id, self.key_secret),
            # Razorpay's flag is the inverse of ours: it asks
            # whether to cancel at the cycle end.
            json={"cancel_at_cycle_end": 1 if at_period_end else 0},
            timeout=20,
        )

        response.raise_for_status()

    def verify(self, body: bytes, signature: str) -> bool:
        """
        HMAC-SHA256 of the raw body with the webhook secret.

        The *raw* body. Parsing the JSON and re-encoding it
        changes the bytes - key order, spacing - and the
        signature then never matches, so the route hands the
        bytes straight through.
        """
        if not self.webhook_secret:
            # No secret configured means no way to tell a real
            # webhook from a forged one. Refusing everything is
            # the only safe answer; accepting everything would
            # let anybody grant themselves a plan.
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature or "")

    def read(self, payload: dict) -> BillingUpdate | None:
        kind = payload.get("event", "")

        if kind not in STATES:
            return None

        entity = (
            payload.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
        )

        subscription_id = entity.get("id")

        if not subscription_id:
            return None

        # Unix seconds. current_end is when what they have just
        # paid for runs out, which is exactly the paid-until date
        # the workspace needs.
        end = entity.get("current_end")

        return BillingUpdate(
            event_id=str(
                payload.get("id")
                or f"{kind}:{subscription_id}:{end or ''}"
            ),
            kind=kind,
            subscription_id=subscription_id,
            status=STATES[kind],
            paid_until=(
                datetime.fromtimestamp(end, tz=UTC) if end else None
            ),
            # Razorpay counts in paise; everything here is whole
            # rupees.
            amount=_rupees(entity.get("plan_amount")),
        )


def _rupees(paise: object) -> int | None:
    if paise is None:
        return None

    try:
        return int(paise) // 100
    except (TypeError, ValueError):
        return None
