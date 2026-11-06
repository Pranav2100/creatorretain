from app.core.settings import settings
from app.services.billing.base import (
    BillingProvider,
    BillingUpdate,
    Checkout,
)
from app.services.billing.fake import FakeBillingProvider
from app.services.billing.razorpay import RazorpayBillingProvider

__all__ = [
    "BillingProvider",
    "BillingUpdate",
    "Checkout",
    "FakeBillingProvider",
    "RazorpayBillingProvider",
    "get_billing_provider",
]

_PROVIDERS: dict[str, type[BillingProvider]] = {
    "fake": FakeBillingProvider,
    "razorpay": RazorpayBillingProvider,
}

# One instance, not one per request.
#
# The fake keeps a record of what it was asked to do, which the
# suites read back - a fresh instance per call would forget it
# between the request that started a subscription and the
# assertion about it. The real one is stateless and does not
# care either way.
_live: BillingProvider | None = None


def get_billing_provider() -> BillingProvider:
    global _live

    if _live is not None:
        return _live

    provider = _PROVIDERS.get(settings.BILLING_PROVIDER.lower())

    if provider is None:
        raise ValueError(
            f"Unknown BILLING_PROVIDER "
            f"'{settings.BILLING_PROVIDER}'. Expected one of: "
            f"{', '.join(_PROVIDERS)}."
        )

    _live = provider()

    return _live


def reset_billing_provider() -> None:
    """Drop the cached instance. For tests."""
    global _live
    _live = None
