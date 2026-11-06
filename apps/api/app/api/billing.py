from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import (
    get_billing_service,
    get_workspace_member_service,
)
from app.api.errors import http_error
from app.common.enums.workspace_plan import WorkspacePlan
from app.database.models.user import User
from app.services.billing.service import BillingService
from app.services.workspace_member import WorkspaceMemberService

router = APIRouter(prefix="/billing", tags=["Billing"])


class StartRequest(BaseModel):
    plan: WorkspacePlan


class CheckoutResponse(BaseModel):
    subscription_id: str
    pay_url: str | None


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    amount: int | None
    currency: str
    current_period_end: str | None
    cancelled: bool


class BillingResponse(BaseModel):
    plans: list[dict]
    subscription: SubscriptionResponse | None


def _shown(subscription) -> SubscriptionResponse | None:
    if subscription is None:
        return None

    return SubscriptionResponse(
        plan=subscription.plan.value,
        status=subscription.status.value,
        amount=subscription.amount,
        currency=subscription.currency,
        current_period_end=(
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
        cancelled=subscription.cancelled_at is not None,
    )


@router.get(
    "",
    response_model=BillingResponse,
    summary="What this workspace can buy, and what it is paying for",
)
def read_billing(
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)

        return BillingResponse(
            plans=service.catalogue(context),
            subscription=_shown(service.current(context)),
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/subscription",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start paying for a plan",
)
def start_subscription(
    payload: StartRequest,
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    """
    Returns somewhere to go and pay.

    The plan is not granted here. It arrives when the provider
    says it was paid for - otherwise abandoning a checkout would
    be a free month.
    """
    try:
        context = members.resolve_context(current_user.id)
        checkout = service.start(context, payload.plan)
        service.repository.db.commit()

        return CheckoutResponse(
            subscription_id=checkout.subscription_id,
            pay_url=checkout.pay_url,
        )

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Stop a plan renewing",
)
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    """
    Stops the next renewal and nothing else.

    What has already been paid for is kept until the date it
    runs out, which is why this does not touch the plan.
    """
    try:
        context = members.resolve_context(current_user.id)
        cancelled = service.cancel(context)
        service.repository.db.commit()

        return _shown(cancelled)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/webhook",
    summary="Where the payment provider tells us what happened",
)
async def webhook(
    request: Request,
    service: BillingService = Depends(get_billing_service),
):
    """
    Unauthenticated by necessity, verified by signature.

    A provider cannot sign in, so this is the one route anybody
    on the internet can reach. What makes it safe is that the
    body is checked against a shared secret before a single
    field of it is believed - without that, granting yourself
    Business is a matter of describing it convincingly.

    The **raw** bytes are passed through deliberately. Parsing
    the JSON and re-encoding it changes key order and spacing,
    and the signature would never match again.
    """
    body = await request.body()

    signature = (
        request.headers.get("X-Razorpay-Signature")
        or request.headers.get("X-Webhook-Signature")
        or ""
    )

    try:
        result = service.handle_webhook(body, signature)
        service.repository.db.commit()

        return result

    except ValueError as e:
        raise http_error(e)
