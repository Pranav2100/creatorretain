from app.common.enums.workspace_plan import WorkspacePlan
from app.common.enums.workspace_type import WorkspaceType

# --------------------------------------------------------------
# What each plan costs, per month, in whole rupees.
#
# PLACEHOLDERS. Nobody has decided the real numbers yet. They are
# here, in one table, rather than scattered through the billing
# code, so deciding them later is editing this file.
#
# Every one is under 15,000 on purpose, and that is not a
# coincidence or a guess about what the market will bear. India's
# rules on recurring card payments let an auto-debit run without
# the customer re-authenticating only up to 15,000 rupees; above
# it, every single monthly charge needs an OTP or a UPI PIN. A
# plan priced at 20,000 would ask every customer to re-authorise
# every month, and most of them would eventually not bother.
#
# So the threshold is a pricing constraint, not a technical
# detail. If a plan ever needs to cost more than this, the
# answer is annual billing split into instalments under the
# limit, not a bigger monthly number.
#
# None means the plan cannot be bought: Free needs no payment,
# and MANAGED and VERIFIED are arranged by talking to somebody.
# --------------------------------------------------------------

AUTO_DEBIT_CEILING = 15_000

PRICES: dict[tuple[WorkspaceType, WorkspacePlan], int | None] = {
    (WorkspaceType.BRAND, WorkspacePlan.FREE): None,
    (WorkspaceType.BRAND, WorkspacePlan.PRO): 2_499,
    (WorkspaceType.BRAND, WorkspacePlan.BUSINESS): 7_999,
    (WorkspaceType.BRAND, WorkspacePlan.MANAGED): None,
    (WorkspaceType.CREATOR, WorkspacePlan.FREE): None,
    (WorkspaceType.CREATOR, WorkspacePlan.VERIFIED): None,
    (WorkspaceType.AGENCY, WorkspacePlan.FREE): None,
    (WorkspaceType.AGENCY, WorkspacePlan.PRO): 4_999,
    (WorkspaceType.AGENCY, WorkspacePlan.BUSINESS): 12_999,
}


def price_for(
    workspace_type: WorkspaceType,
    plan: WorkspacePlan,
) -> int | None:
    """
    Monthly price in whole rupees, or None if it is not for sale.

    Not for sale covers three different things that all behave
    the same way here: Free costs nothing, VERIFIED is granted
    rather than bought, and MANAGED is a conversation. The
    interface shows each of them differently; billing treats
    them alike, because none of them involves taking money.
    """
    return PRICES.get((workspace_type, plan))


def is_purchasable(
    workspace_type: WorkspaceType,
    plan: WorkspacePlan,
) -> bool:
    return price_for(workspace_type, plan) is not None


def needs_reauthorisation(amount: int) -> bool:
    """
    Whether every monthly charge at this price will ask the
    customer to authenticate again.

    Exposed so the interface can warn rather than let somebody
    set a price that quietly halves their renewal rate.
    """
    return amount > AUTO_DEBIT_CEILING
