import json
from datetime import UTC, datetime

from app.common.entitlements.pricing import (
    PRICES,
    is_purchasable,
    price_for,
)
from app.common.enums.subscription import SubscriptionStatus
from app.common.enums.workspace_plan import WorkspacePlan
from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.permissions import WorkspacePermission
from app.database.models.subscription import Subscription
from app.database.repositories.billing import BillingRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.services.billing.base import BillingProvider, Checkout
from app.services.workspace_member import WorkspaceContext


# Which (type, plan) pairs exist at all. Taken from the pricing
# table rather than listed again, so the two cannot disagree
# about which plans a creator even has.
_KNOWN = set(PRICES)


class BillingService:
    """
    Taking money for plans.

    One rule shapes all of this: **the provider grants the plan,
    not the request**. Starting a subscription changes nothing
    about what a workspace can do - it only creates a pending row
    and sends the person off to pay. The plan arrives when a
    signed webhook says it was paid for.

    The alternative, granting on the way out and revoking if
    payment fails, means anybody who can click Upgrade gets a
    month of Business for the cost of abandoning a checkout.
    """

    def __init__(
        self,
        repository: BillingRepository,
        workspace_repository: WorkspaceRepository,
        provider: BillingProvider,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.provider = provider

    def _now(self) -> datetime:
        return datetime.now(UTC)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def current(
        self,
        context: WorkspaceContext,
    ) -> Subscription | None:
        context.require(
            WorkspacePermission.MANAGE_BILLING,
            "Only the owner can see billing.",
        )

        return self.repository.live_for_workspace(
            context.workspace_id,
        )

    # ------------------------------------------------------------------
    # Buying
    # ------------------------------------------------------------------

    def start(
        self,
        context: WorkspaceContext,
        plan: WorkspacePlan,
    ) -> Checkout:
        context.require(
            WorkspacePermission.MANAGE_BILLING,
            "Only the owner can change the plan.",
        )

        workspace = context.workspace

        if not is_purchasable(workspace.workspace_type, plan):
            # Covers three different things that behave alike
            # here: Free costs nothing, Verified is granted, and
            # Managed is a conversation.
            raise ConflictError(
                f"The {plan.value} plan is not something you can "
                f"buy here."
            )

        if workspace.effective_plan == plan:
            raise ConflictError(f"You are already on {plan.value}.")

        existing = self.repository.live_for_workspace(workspace.id)

        if existing is not None and existing.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PAST_DUE,
        ):
            # Changing plan while paying for another one needs
            # the old one stopped first, or the provider bills
            # for both. Deliberately an error rather than a
            # silent swap: a swap mid-cycle raises refund
            # questions nobody has answered yet.
            raise ConflictError(
                "Cancel your current plan before starting another."
            )

        if existing is not None and existing.status in (
            SubscriptionStatus.PENDING,
            SubscriptionStatus.CANCELLING,
        ):
            # Pressing Choose again supersedes the last attempt
            # rather than stacking on top of it.
            #
            # Without this, every click creates another
            # subscription at the provider: somebody who tries
            # Pro, thinks better of it and tries Business ends up
            # with two live checkouts, and if they pay both they
            # are charged twice. One cancel would only clear one
            # of them, so the page would go on saying a payment
            # was on its way.
            #
            # A CANCELLING one is included because it is already
            # on its way out; starting again is the clearest way
            # to say "no, keep paying, just for this instead".
            self._supersede(existing)

        checkout = self.provider.start(
            plan=plan,
            workspace_id=str(workspace.id),
            email=self._billing_email(context),
            name=workspace.display_name,
        )

        self.repository.create(
            workspace_id=workspace.id,
            provider=self.provider.name,
            provider_subscription_id=checkout.subscription_id,
            plan=plan,
            amount=price_for(workspace.workspace_type, plan),
        )

        # Note what is *not* here: nothing touches workspace.plan.
        # They have not paid yet.

        return checkout

    def cancel(self, context: WorkspaceContext) -> Subscription:
        context.require(
            WorkspacePermission.MANAGE_BILLING,
            "Only the owner can change the plan.",
        )

        live = self.repository.live_for_workspace(
            context.workspace_id,
        )

        if live is None:
            raise NotFoundError("There is nothing to cancel.")

        if live.status == SubscriptionStatus.CANCELLING:
            # Already stopping. Telling the provider to cancel a
            # second time is at best wasted and at worst an
            # error from them, and the person has not asked for
            # anything different from what is already happening.
            raise ConflictError(
                "That plan is already set to stop renewing."
            )

        # A subscription nobody has paid for yet is not
        # "cancelling at the end of the period" - there is no
        # period. It just stops, immediately and completely.
        #
        # Without this, abandoning a checkout leaves a pending
        # row for ever and the page goes on claiming it is
        # waiting for a payment that is never coming.
        pending = live.status == SubscriptionStatus.PENDING

        self.provider.cancel(
            live.provider_subscription_id,
            at_period_end=not pending,
        )

        live.status = (
            SubscriptionStatus.ENDED
            if pending
            else SubscriptionStatus.CANCELLING
        )
        live.cancelled_at = self._now()

        # Anything else unpaid goes with it. Starting a
        # subscription now supersedes the last attempt, so there
        # should be nothing here - but a database that collected
        # stacked rows before that was true would otherwise need
        # one click per row to get clean, with the page still
        # claiming a payment was coming in between.
        for stale in self.repository.pending_for_workspace(
            context.workspace_id,
        ):
            if stale.id != live.id:
                self._supersede(stale)

        # plan_expires_at is deliberately untouched. Somebody who
        # cancels on the third has paid for that month and keeps
        # it; the plan lapses when the date passes, which
        # effective_plan already handles without anybody running
        # anything.
        self.repository.db.flush()

        return live

    def _supersede(self, subscription: Subscription) -> None:
        """
        Ends a subscription nobody is paying for yet, so another
        can take its place.

        Only ever used on PENDING or CANCELLING rows, so this
        cannot take away something somebody is paying for:
        plan_expires_at is untouched either way, and a plan
        already paid for runs to the date on the workspace.
        """
        if subscription.cancelled_at is None:
            # Already-cancelling rows have been through this at
            # the provider once. Telling them twice is the same
            # mistake the double-cancel guard exists to prevent.
            self.provider.cancel(
                subscription.provider_subscription_id,
                at_period_end=False,
            )
            subscription.cancelled_at = self._now()

        subscription.status = SubscriptionStatus.ENDED

    def _billing_email(self, context: WorkspaceContext) -> str:
        membership = context.membership

        if membership is not None and membership.user is not None:
            return membership.user.email

        owner = context.workspace.owner

        return owner.email if owner is not None else ""

    # ------------------------------------------------------------------
    # What the provider tells us
    # ------------------------------------------------------------------

    def handle_webhook(
        self,
        body: bytes,
        signature: str,
    ) -> dict:
        """
        Apply one webhook, or decline to.

        Order matters here. The signature is checked before
        anything is parsed, because an unverified payload is just
        a string a stranger sent us. Then the event id is checked
        before anything is written, because providers retry and a
        renewal applied twice would hand out a month nobody paid
        for.
        """
        if not self.provider.verify(body, signature):
            raise PermissionDeniedError(
                "That webhook did not come from the provider."
            )

        try:
            payload = json.loads(body)
        except ValueError:
            raise ConflictError("That webhook was not JSON.")

        update = self.provider.read(payload)

        if update is None:
            # Most events are not ours to act on. Saying so
            # plainly, with a 2xx, stops the provider retrying
            # something we will never want.
            return {"handled": False, "reason": "not interesting"}

        if not update.event_id:
            raise ConflictError("That webhook had no id.")

        if self.repository.already_handled(
            self.provider.name,
            update.event_id,
        ):
            return {"handled": False, "reason": "already seen"}

        subscription = self.repository.by_provider_ref(
            self.provider.name,
            update.subscription_id,
        )

        if subscription is None:
            # Recorded anyway, so the provider stops retrying an
            # event about something we have no record of - which
            # is usually a subscription created against a
            # different environment's keys.
            self.repository.record_event(
                self.provider.name,
                update.event_id,
                update.kind,
                update.subscription_id,
            )

            return {"handled": False, "reason": "unknown subscription"}

        self._apply(subscription, update)

        self.repository.record_event(
            self.provider.name,
            update.event_id,
            update.kind,
            update.subscription_id,
        )

        return {
            "handled": True,
            "status": subscription.status.value,
        }

    def _apply(self, subscription: Subscription, update) -> None:
        if update.status is not None:
            subscription.status = update.status

        if update.amount is not None:
            subscription.amount = update.amount

        if update.paid_until is not None:
            subscription.current_period_end = update.paid_until

        workspace = self.workspace_repository.get(
            subscription.workspace_id,
        )

        if workspace is None:
            return

        if subscription.status.is_live:
            workspace.plan = subscription.plan

            # Only ever forward.
            #
            # Webhooks can arrive late, out of order, or twice
            # with different dates. Taking the later of the two
            # means a stale event cannot shorten something
            # already paid for, which is the direction that
            # matters: being generous by a month is a smaller
            # mistake than taking away a month somebody bought.
            if update.paid_until is not None:
                current = workspace.plan_expires_at

                if current is not None and current.tzinfo is None:
                    current = current.replace(tzinfo=UTC)

                workspace.plan_expires_at = (
                    update.paid_until
                    if current is None
                    else max(current, update.paid_until)
                )

        # Nothing happens on ENDED. The date already on the
        # workspace is what they paid for, and effective_plan
        # drops them to Free the moment it passes - so ending a
        # subscription needs no action here and no job anywhere.

        self.repository.db.flush()

    # ------------------------------------------------------------------
    # For the page
    # ------------------------------------------------------------------

    def catalogue(self, context: WorkspaceContext) -> list[dict]:
        """
        Every plan for this kind of workspace, with its price.

        Including the ones that cannot be bought, each saying why
        - a plan that simply vanishes from the list looks like a
        bug, and "talk to us" is a real answer.
        """
        out: list[dict] = []
        workspace_type = context.workspace.workspace_type

        for plan in WorkspacePlan:
            price = price_for(workspace_type, plan)
            known = (workspace_type, plan) in _KNOWN

            if not known:
                continue

            out.append(
                {
                    "plan": plan.value,
                    "price": price,
                    "purchasable": price is not None,
                    "current": context.workspace.effective_plan
                    == plan,
                }
            )

        return out
