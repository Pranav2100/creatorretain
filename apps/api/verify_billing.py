"""
Taking money, and refusing to be told lies about it.

The webhook is the only route in this application that anybody
on the internet can reach without signing in, and what it says
decides who has paid. So most of this file is about not
believing it: a forged signature, a replayed event, an event
about somebody else's subscription, an event with no id.

The other half is the rule the whole design rests on - **the
provider grants the plan, not the request**. Clicking Upgrade
must change nothing at all. If it did, abandoning a checkout
would be a free month, and nobody would ever pay twice.

Runs against the fake provider, which signs its webhooks the
same way a real one does and checks them the same way. You
cannot charge a card in a test suite; you can make sure
everything around the charge is right.
"""

import json
import os
from datetime import UTC, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["BILLING_PROVIDER"] = "fake"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database.registry  # noqa: F401,E402
from app.common.enums.subscription import (  # noqa: E402
    SubscriptionStatus,
)
from app.common.enums.workspace_plan import WorkspacePlan  # noqa: E402
from app.database.models.base import Base  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSession = sessionmaker(
    bind=engine, autoflush=False, autocommit=False
)
Base.metadata.create_all(engine)

import app.api.dependencies.services as services_module  # noqa: E402
from app.services.email.base import EmailSender  # noqa: E402


class _Silent(EmailSender):
    def send(self, message):
        pass


services_module.get_email_sender = lambda: _Silent()

from fastapi.testclient import TestClient  # noqa: E402

from app.database.models.subscription import (  # noqa: E402
    Subscription,
)
from app.database.models.workspace import Workspace  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.billing import get_billing_provider  # noqa: E402
from app.services.billing.fake import (  # noqa: E402
    FakeBillingProvider,
)


def override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)

PROVIDER: FakeBillingProvider = get_billing_provider()

PASSED: list[str] = []
FAILED: list[str] = []

PASSWORD = "Str0ng!Passw0rd"


def ok(label):
    PASSED.append(label)
    print("PASS  " + label)


def bad(label, detail=""):
    FAILED.append(label)
    print("FAIL  " + label)

    if detail:
        print("        " + detail)


def check(label, response, expected, contains=None):
    good = response.status_code == expected

    if good and contains:
        good = contains.lower() in response.text.lower()

    if good:
        ok(label)
    else:
        bad(label, f"[{response.status_code}] {response.text[:200]}")

    return response


# ----------------------------------------------------------------------
# Harness
# ----------------------------------------------------------------------


def register(email, first="Test"):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "first_name": first,
            "last_name": "Person",
        },
    )

    login = client.post(
        "/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text

    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    client.patch(
        "/auth/me",
        json={"job_title": "Owner", "phone": "+919876543210"},
        headers=headers,
    )

    return headers


def workspace(headers, name, slug, kind="agency"):
    r = client.post(
        "/workspaces",
        json={
            "display_name": name,
            "username": slug,
            "workspace_type": kind,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    return r.json()["workspace"]["id"]


def join(owner, email, role, first):
    person = register(email, first)

    invited = client.post(
        "/workspace-invitations/invite",
        json={"email": email, "role": role},
        headers=owner,
    )
    assert invited.status_code == 200, invited.text

    mine = client.get(
        "/workspace-invitations", headers=person
    ).json()["invitations"]

    live = next(i for i in mine if i["status"] == "pending")

    client.post(
        f"/workspace-invitations/{live['id']}/accept",
        headers=person,
    )

    return person


def plan_of(slug: str) -> tuple[str, object]:
    """The stored plan and expiry, straight from the database."""
    db = TestSession()
    try:
        ws = db.query(Workspace).filter_by(slug=slug).first()
        return ws.plan.value, ws.plan_expires_at
    finally:
        db.close()


def subscription_rows() -> list[Subscription]:
    db = TestSession()
    try:
        return db.query(Subscription).all()
    finally:
        db.close()


def post_webhook(body: bytes, signature: str):
    return client.post(
        "/billing/webhook",
        content=body,
        headers={
            "X-Razorpay-Signature": signature,
            "Content-Type": "application/json",
        },
    )


# ----------------------------------------------------------------------
# Cast
# ----------------------------------------------------------------------

owner = register("owner@billing.example", "Olive")
workspace(owner, "TalentX", "talentx_billing", "agency")

admin = join(owner, "admin@billing.example", "admin", "Adam")

creator = register("creator@billing.example", "Nina")
workspace(creator, "Nina Cooks", "nina_billing", "creator")

print()
print("=" * 62)
print("What is on sale")
print("=" * 62)

listing = check(
    "the owner can read the plans",
    client.get("/billing", headers=owner),
    200,
)

if listing.status_code == 200:
    body = listing.json()
    plans = {p["plan"]: p for p in body["plans"]}

    if set(plans) == {"free", "pro", "business"}:
        ok("an agency is offered free, pro and business")
    else:
        bad("wrong plans for an agency", str(sorted(plans)))

    if plans.get("pro", {}).get("price") == 4999:
        ok("with a price on the ones you can buy")
    else:
        bad("no price on pro", str(plans.get("pro")))

    if plans.get("free", {}).get("purchasable") is False:
        ok("and free is listed but not for sale")
    else:
        bad("free looks purchasable")

    if body["subscription"] is None:
        ok("nobody is paying for anything yet")
    else:
        bad("a subscription appeared from nowhere")

creator_listing = client.get("/billing", headers=creator)

if creator_listing.status_code == 200:
    creator_plans = {
        p["plan"]: p for p in creator_listing.json()["plans"]
    }

    if set(creator_plans) == {"free", "verified"}:
        ok("a creator sees their own two plans")
    else:
        bad("wrong plans for a creator", str(sorted(creator_plans)))

    if creator_plans["verified"]["purchasable"] is False:
        ok("and verified is granted, not bought")
    else:
        bad("verified is for sale")

check(
    "an admin cannot see billing - it is the owner's",
    client.get("/billing", headers=admin),
    403,
)

print()
print("=" * 62)
print("Clicking Upgrade grants nothing")
print("=" * 62)

started = check(
    "the owner can start a subscription",
    client.post(
        "/billing/subscription",
        json={"plan": "pro"},
        headers=owner,
    ),
    201,
)

subscription_id = (
    started.json()["subscription_id"]
    if started.status_code == 201
    else None
)

if started.status_code == 201 and started.json().get("pay_url"):
    ok("and is given somewhere to go and pay")
else:
    bad("no payment link came back")

stored_plan, expires = plan_of("talentx_billing")

# The whole design rests on this one.
if stored_plan == "free" and expires is None:
    ok("the workspace is still on free, because nothing is paid")
else:
    bad(
        "starting a checkout granted the plan",
        f"plan={stored_plan} expires={expires}",
    )

rows = subscription_rows()

if len(rows) == 1 and rows[0].status.value == "pending":
    ok("there is one pending subscription waiting")
else:
    bad(
        "wrong subscription state",
        str([(r.status.value, r.plan.value) for r in rows]),
    )

check(
    "an admin cannot start one",
    client.post(
        "/billing/subscription",
        json={"plan": "pro"},
        headers=admin,
    ),
    403,
)

check(
    "nobody can buy free",
    client.post(
        "/billing/subscription",
        json={"plan": "free"},
        headers=owner,
    ),
    409,
    "not something you can buy",
)

check(
    "nor a plan that belongs to another kind of workspace",
    client.post(
        "/billing/subscription",
        json={"plan": "verified"},
        headers=owner,
    ),
    409,
)

print()
print("=" * 62)
print("An abandoned checkout can be cleared away")
print("=" * 62)

# Somebody clicks Choose, thinks better of it, and never pays.
# Without this the pending row sits there for ever and the page
# goes on saying a payment is coming.
abandoned = check(
    "a pending subscription can be cancelled",
    client.delete("/billing/subscription", headers=owner),
    200,
)

if abandoned.status_code == 200:
    if abandoned.json()["status"] == "ended":
        ok("and it ends outright rather than 'cancelling'")
    else:
        bad(
            "a pending subscription was cancelled at period end",
            abandoned.text[:140],
        )

stored_plan, expires = plan_of("talentx_billing")

if stored_plan == "free" and expires is None:
    ok("nothing was granted or taken away by any of that")
else:
    bad(f"plan={stored_plan} expires={expires}")

# And they can start again.
restarted = check(
    "and a new subscription can be started afterwards",
    client.post(
        "/billing/subscription",
        json={"plan": "pro"},
        headers=owner,
    ),
    201,
)

subscription_id = (
    restarted.json()["subscription_id"]
    if restarted.status_code == 201
    else subscription_id
)

print()
print("=" * 62)
print("The webhook is not believed without a signature")
print("=" * 62)

body, signature = FakeBillingProvider.event(
    "subscription.activated",
    subscription_id or "nope",
)

check(
    "an unsigned webhook is refused",
    post_webhook(body, ""),
    403,
    "did not come from",
)

check(
    "a wrongly signed one is refused",
    post_webhook(body, "deadbeef"),
    403,
)

# The classic: take a real signed event and change the body.
tampered = json.loads(body)
tampered["subscription_id"] = "fake_sub_somebodyelse"

check(
    "a real signature on a changed body is refused",
    post_webhook(json.dumps(tampered).encode(), signature),
    403,
)

stored_plan, _ = plan_of("talentx_billing")

if stored_plan == "free":
    ok("and none of that granted anything")
else:
    bad(f"a forged webhook moved the plan to {stored_plan}")

print()
print("=" * 62)
print("A properly signed one does the job")
print("=" * 62)

paid = check(
    "the activation is accepted",
    post_webhook(body, signature),
    200,
)

if paid.status_code == 200 and paid.json().get("handled"):
    ok("and reports that it acted on it")
else:
    bad("the webhook was not acted on", paid.text[:160])

stored_plan, expires = plan_of("talentx_billing")

if stored_plan == "pro":
    ok("now the workspace is on pro")
else:
    bad(f"the plan is {stored_plan}, not pro")

if expires is not None:
    ok(f"with a paid-until date ({expires.date()})")
else:
    bad("no expiry was set")

# Entitlements have to follow, or the plan is just a label.
after = client.get("/workspace-plan", headers=owner)

if after.status_code == 200 and after.json().get("plan") == "pro":
    ok("and the plan endpoint agrees")
else:
    bad("the plan endpoint disagrees", after.text[:160])

print()
print("=" * 62)
print("The same event twice changes nothing twice")
print("=" * 62)

_, first_expiry = plan_of("talentx_billing")

replay = post_webhook(body, signature)

check("a replayed webhook is accepted politely", replay, 200)

if replay.status_code == 200 and not replay.json().get("handled"):
    ok("but says it did nothing")
else:
    bad("a replay was acted on again", replay.text[:160])

_, second_expiry = plan_of("talentx_billing")

if first_expiry == second_expiry:
    ok("and the paid-until date did not move")
else:
    bad(
        "a replay extended the subscription",
        f"{first_expiry} -> {second_expiry}",
    )

print()
print("=" * 62)
print("A renewal moves the date; a stale one cannot pull it back")
print("=" * 62)

renewal, renewal_sig = FakeBillingProvider.event(
    "subscription.charged",
    subscription_id or "nope",
    days=60,
)

post_webhook(renewal, renewal_sig)

_, renewed = plan_of("talentx_billing")

if renewed and second_expiry and renewed > second_expiry:
    ok("a renewal pushes the date forward")
else:
    bad(f"the renewal did not extend: {second_expiry} -> {renewed}")

# Webhooks arrive late and out of order. An older one must not
# shorten something already paid for.
stale, stale_sig = FakeBillingProvider.event(
    "subscription.charged",
    subscription_id or "nope",
    days=5,
)

post_webhook(stale, stale_sig)

_, after_stale = plan_of("talentx_billing")

if after_stale == renewed:
    ok("and an older one arriving late cannot shorten it")
else:
    bad(
        "a stale webhook pulled the date back",
        f"{renewed} -> {after_stale}",
    )

print()
print("=" * 62)
print("An event about a subscription we do not know")
print("=" * 62)

stranger, stranger_sig = FakeBillingProvider.event(
    "subscription.activated",
    "fake_sub_neverseen",
)

unknown = check(
    "it is accepted rather than retried for ever",
    post_webhook(stranger, stranger_sig),
    200,
)

if unknown.status_code == 200 and not unknown.json().get("handled"):
    ok("and reports that it did nothing")
else:
    bad("an unknown subscription was acted on")

print()
print("=" * 62)
print("Cancelling keeps what was paid for")
print("=" * 62)

_, before_cancel = plan_of("talentx_billing")

cancelled = check(
    "the owner can cancel",
    client.delete("/billing/subscription", headers=owner),
    200,
)

if cancelled.status_code == 200:
    if cancelled.json()["status"] == "cancelling":
        ok("the subscription reads as cancelling")
    else:
        bad("wrong status after cancelling", cancelled.text[:120])

    if subscription_id in PROVIDER.cancelled:
        ok("and the provider was actually told")
    else:
        bad("the provider was never told to cancel")

stored_plan, after_cancel = plan_of("talentx_billing")

if stored_plan == "pro" and after_cancel == before_cancel:
    ok("the plan and its date are untouched - they paid for it")
else:
    bad(
        "cancelling took away a paid month",
        f"plan={stored_plan} {before_cancel} -> {after_cancel}",
    )

check(
    "cancelling twice is refused, not done twice",
    client.delete("/billing/subscription", headers=owner),
    409,
    "already set to stop",
)

if PROVIDER.cancelled.count(subscription_id) == 1:
    ok("and the provider was told exactly once")
else:
    bad(
        "the provider was told to cancel more than once",
        str(PROVIDER.cancelled),
    )

print()
print("=" * 62)
print("And when the date passes, the plan lapses on its own")
print("=" * 62)

# Nothing runs. effective_plan is computed, so moving the date
# into the past is the whole of "the subscription ran out".
db = TestSession()
try:
    ws = db.query(Workspace).filter_by(slug="talentx_billing").first()
    ws.plan_expires_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()
finally:
    db.close()

lapsed = client.get("/workspace-plan", headers=owner)

if lapsed.status_code == 200 and lapsed.json()["plan"] == "free":
    ok("an expired plan reads as free with nothing having run")
else:
    bad("the lapsed plan did not fall back", lapsed.text[:160])

stored_plan, _ = plan_of("talentx_billing")

if stored_plan == "pro":
    ok("while the stored plan still remembers what was bought")
else:
    bad("the stored plan was overwritten")

print()
print("=" * 62)
print("Changing your mind before paying")
print("=" * 62)

# Found by Pranav clicking the real page: the box went on saying
# a payment was on its way after he had cleared it. Every press
# of Choose used to create another subscription at the provider,
# and a cancel only ended one of them - so two presses meant two
# live checkouts and, if both were paid, two charges.

for leftover in subscription_rows():
    if leftover.status != SubscriptionStatus.ENDED:
        client.delete("/billing/subscription", headers=owner)
        break

# Whatever the earlier webhooks left this workspace on. The
# point below is that none of this moves it, not that it is Free.
plan_before = plan_of("talentx_billing")

client.post(
    "/billing/subscription",
    json={"plan": "pro"},
    headers=owner,
)
client.post(
    "/billing/subscription",
    json={"plan": "business"},
    headers=owner,
)

unpaid = [
    row
    for row in subscription_rows()
    if row.status == SubscriptionStatus.PENDING
]

if len(unpaid) == 1:
    ok("choosing twice supersedes rather than stacking")
else:
    bad(
        "two presses of Choose left more than one live checkout",
        f"{len(unpaid)} pending: "
        + ", ".join(f"{r.plan.value}/{r.status.value}" for r in unpaid),
    )

if unpaid and unpaid[0].plan == WorkspacePlan.BUSINESS:
    ok("and the one left is the plan chosen last")
else:
    bad("the superseded plan is the one still waiting to be paid")

check(
    "one cancel clears what is waiting",
    client.delete("/billing/subscription", headers=owner),
    200,
)

if client.get("/billing", headers=owner).json()["subscription"] is None:
    ok("and the page stops claiming a payment is coming")
else:
    bad("the page still shows a subscription after cancelling")

if plan_of("talentx_billing") == plan_before:
    ok("none of which moved the plan either way")
else:
    bad(
        "an abandoned checkout changed the plan",
        f"{plan_before} became {plan_of('talentx_billing')}",
    )

print()
print("=" * 62)
print("Signed out, and other people's workspaces")
print("=" * 62)

check(
    "signed out, billing is not readable",
    client.get("/billing"),
    401,
)

check(
    "signed out, a subscription cannot be started",
    client.post("/billing/subscription", json={"plan": "pro"}),
    401,
)

if client.get("/billing", headers=creator).json()[
    "subscription"
] is None:
    ok("the creator sees none of the agency's billing")
else:
    bad("billing leaked across workspaces")

print()
print(f"{len(PASSED)} passed, {len(FAILED)} failed")

if FAILED:
    print()
    for label in FAILED:
        print("  FAILED: " + label)
