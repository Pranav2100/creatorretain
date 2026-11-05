"""
Who gets told what, and when it is better to say nothing.

A notification system is judged by its restraint. Sending is the
easy half; the half worth testing is everything it declines to
send - to the person who did the thing, to the read-only Member
who cannot act on it, to somebody who turned that category off,
twice about the same event, or at all once the thing stopped
mattering.

The outbox makes that testable, because queuing and sending are
separate steps. Most of this file queues something and then
reads the outbox, without any email going anywhere.
"""

import os
from datetime import UTC, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database.registry  # noqa: F401,E402
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
from app.services.email.base import (  # noqa: E402
    EmailMessage,
    EmailSender,
)


class Recorder(EmailSender):
    """
    Keeps every email instead of sending it, and can be told to
    fail - which is the only way to test what happens when a
    provider is down.
    """

    def __init__(self):
        self.sent: list[EmailMessage] = []
        self.explode = False

    def send(self, message: EmailMessage) -> None:
        if self.explode:
            raise RuntimeError("the provider is having a day")

        self.sent.append(message)


POSTMAN = Recorder()

# Patched in three places because three of them resolve it: the
# dependency factory the API uses, the module it was imported
# from, and the drain script, which builds its own. Patching one
# and not the others is how a console email appeared in the
# middle of a test run that thought it had intercepted
# everything.
import app.services.email as email_module  # noqa: E402

services_module.get_email_sender = lambda: POSTMAN
email_module.get_email_sender = lambda: POSTMAN

from fastapi.testclient import TestClient  # noqa: E402

from app.common.enums.notification import (  # noqa: E402
    NotificationKind,
)
from app.database.models.notification import (  # noqa: E402
    MAX_ATTEMPTS,
    Notification,
)
from app.database.models.content_category import (  # noqa: E402
    ContentCategory,
)
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


def override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)

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
# Looking in the outbox
# ----------------------------------------------------------------------


def outbox(kind: NotificationKind | None = None) -> list[Notification]:
    db = TestSession()
    try:
        query = db.query(Notification)

        if kind is not None:
            query = query.filter(Notification.kind == kind)

        return query.order_by(Notification.created_at).all()
    finally:
        db.close()


def queued_for(email: str, kind: NotificationKind) -> int:
    return len(
        [
            n
            for n in outbox(kind)
            if n.to_email == email
            and n.sent_at is None
            and n.dropped_at is None
        ]
    )


def clear_outbox() -> None:
    db = TestSession()
    try:
        db.query(Notification).delete()
        db.commit()
    finally:
        db.close()


def make_sendable_now() -> None:
    """Pull every waiting row's send_after into the past."""
    db = TestSession()
    try:
        for row in db.query(Notification).all():
            row.send_after = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()


def drain(limit: int = 50) -> dict:
    db = TestSession()
    try:
        import drain_notifications

        drain_notifications.get_email_sender = lambda: POSTMAN

        return drain_notifications.build(db).drain(limit=limit)
    finally:
        db.close()


# ----------------------------------------------------------------------
# Harness
# ----------------------------------------------------------------------


def register(email, first="Test", last="Person"):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "first_name": first,
            "last_name": last,
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
        json={"job_title": "Talent Manager", "phone": "+919876543210"},
        headers=headers,
    )

    return headers


def me(headers) -> str:
    return client.get("/auth/me", headers=headers).json()["id"]


def workspace(headers, name, slug, kind):
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

    accepted = client.post(
        f"/workspace-invitations/{live['id']}/accept",
        headers=person,
    )
    assert accepted.status_code == 200, accepted.text

    return person


def seed_categories():
    db = TestSession()
    try:
        for slug, name in [("food", "Food"), ("tech", "Tech")]:
            db.add(ContentCategory(slug=slug, name=name))
        db.commit()
    finally:
        db.close()


seed_categories()

# ----------------------------------------------------------------------
# Cast: an agency with four people, and a creator
# ----------------------------------------------------------------------

BRAND = "owner@notify.example"
ADMIN = "admin@notify.example"
MANAGER = "manager@notify.example"
MEMBER = "member@notify.example"
CREATOR = "creator@notify.example"

brand = register(BRAND, "Olive")
brand_ws = workspace(brand, "TalentX", "talentx_notify", "agency")

client.put(
    "/workspace-plan",
    json={"plan": "pro"},
    headers=brand,
)

admin = join(brand, ADMIN, "admin", "Adam")
manager = join(brand, MANAGER, "manager", "Mira")
member = join(brand, MEMBER, "member", "Mo")

creator = register(CREATOR, "Nina")
creator_ws = workspace(creator, "Nina Cooks", "nina_notify", "creator")

client.put(
    "/creator-profile",
    json={
        "display_name": "Nina Cooks",
        "headline": "Home cooking",
        "bio": "Food in Pune, every week, for people who cook at home.",
        "city": "Pune",
        "country": "IN",
        "languages": ["en"],
        "category_ids": [],
    },
    headers=creator,
)

clear_outbox()

print()
print("=" * 62)
print("An offer tells the other side, and nobody else")
print("=" * 62)

offered = client.post(
    "/retainers",
    json={
        "creator_workspace_id": creator_ws,
        "title": "Monthly reels",
        "monthly_amount": "40000.00",
        "deliverables": [{"deliverable_type": "reel", "quantity": 2}],
    },
    headers=brand,
)

check("the brand can make an offer", offered, 201)
retainer_id = offered.json()["id"] if offered.status_code == 201 else None

if queued_for(CREATOR, NotificationKind.OFFER_RECEIVED) == 1:
    ok("the creator has one offer email waiting")
else:
    bad(
        "the creator was not told about the offer",
        str([(n.to_email, n.kind.value) for n in outbox()]),
    )

if queued_for(BRAND, NotificationKind.OFFER_RECEIVED) == 0:
    ok("the person who sent it is not emailed about sending it")
else:
    bad("the sender was emailed their own offer")

for who, label in ((ADMIN, "admin"), (MANAGER, "manager"), (MEMBER, "member")):
    if queued_for(who, NotificationKind.OFFER_RECEIVED) == 0:
        ok(f"nobody on the sending side is told ({label})")
    else:
        bad(f"the {label} on the sending side was emailed")

print()
print("=" * 62)
print("Accepting tells the side that offered, by responsibility")
print("=" * 62)

clear_outbox()

if retainer_id:
    accepted = client.post(
        f"/retainers/{retainer_id}/accept",
        headers=creator,
    )
    check("the creator accepts", accepted, 200)

    if queued_for(BRAND, NotificationKind.OFFER_ACCEPTED) == 1:
        ok("the owner of the agency is told")
    else:
        bad("the agency owner was not told it was accepted")

    if queued_for(ADMIN, NotificationKind.OFFER_ACCEPTED) == 1:
        ok("and so is the admin, who can act on it")
    else:
        bad("the admin was not told")

    # A Member can read every retainer and change none of them.
    # Twenty read-only people emailed about one reel is how a
    # team learns to filter the sender.
    if queued_for(MEMBER, NotificationKind.OFFER_ACCEPTED) == 0:
        ok("a read-only member is not emailed")
    else:
        bad("a read-only member was emailed")

    # A Manager sees only what they are assigned, and is not on
    # this one.
    if queued_for(MANAGER, NotificationKind.OFFER_ACCEPTED) == 0:
        ok("nor a manager who is not on this account")
    else:
        bad("an unassigned manager was emailed")

    if queued_for(CREATOR, NotificationKind.OFFER_ACCEPTED) == 0:
        ok("and the creator is not told what she just did")
    else:
        bad("the creator was emailed her own acceptance")

print()
print("=" * 62)
print("Assigning somebody puts them on the list")
print("=" * 62)

if retainer_id:
    assigned = client.post(
        f"/retainers/{retainer_id}/assignees",
        json={"user_id": me(manager)},
        headers=brand,
    )
    check("the owner assigns the manager", assigned, 200)

    clear_outbox()

    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "pause", "reason": "Travelling for three weeks."},
        headers=creator,
    )

    if queued_for(MANAGER, NotificationKind.PAUSE_REQUESTED) == 1:
        ok("the assigned manager hears about the pause request")
    else:
        bad(
            "the assigned manager was not told",
            str([(n.to_email, n.kind.value) for n in outbox()]),
        )

    if queued_for(MEMBER, NotificationKind.PAUSE_REQUESTED) == 0:
        ok("the read-only member still is not")
    else:
        bad("the member was emailed")

    # The reason travels with it, so the email can say what was
    # asked rather than only that something was.
    waiting = [
        n
        for n in outbox(NotificationKind.PAUSE_REQUESTED)
        if n.to_email == MANAGER
    ]

    if waiting and "Travelling" in (waiting[0].payload or {}).get(
        "note", ""
    ):
        ok("and the reason is carried on the row")
    else:
        bad(
            "the reason did not reach the notification",
            str(waiting[0].payload if waiting else None),
        )

print()
print("=" * 62)
print("One email per thing, however many times it happens")
print("=" * 62)

clear_outbox()

if retainer_id:
    # Reject and ask again - two pause requests, one email while
    # the first is still waiting.
    client.post(
        f"/retainers/{retainer_id}/requests/reject",
        headers=brand,
    )
    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "pause", "reason": "Asking again."},
        headers=creator,
    )
    client.post(
        f"/retainers/{retainer_id}/requests/reject",
        headers=brand,
    )
    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "pause", "reason": "And again."},
        headers=creator,
    )

    count = queued_for(BRAND, NotificationKind.PAUSE_REQUESTED)

    if count == 1:
        ok("three pause requests queue one email")
    else:
        bad(f"three pause requests queued {count} emails")

print()
print("=" * 62)
print("Switches are obeyed, except the one that is not a switch")
print("=" * 62)

clear_outbox()

check(
    "the owner can turn retainer email off",
    client.patch(
        "/auth/me",
        json={"notify_retainers": False},
        headers=brand,
    ),
    200,
)

if retainer_id:
    client.post(
        f"/retainers/{retainer_id}/requests/reject",
        headers=brand,
    )
    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "pause", "reason": "After switching off."},
        headers=creator,
    )

    if queued_for(BRAND, NotificationKind.PAUSE_REQUESTED) == 0:
        ok("and then hears nothing about retainers")
    else:
        bad("a switched-off category still queued an email")

    if queued_for(ADMIN, NotificationKind.PAUSE_REQUESTED) == 1:
        ok("while everybody else still does")
    else:
        bad("turning one person off silenced somebody else")

# Security mail has no switch, which is the point of it.
changed = client.post(
    "/auth/change-password",
    json={
        "current_password": PASSWORD,
        "new_password": "An0ther!Passw0rd",
        "confirm_password": "An0ther!Passw0rd",
    },
    headers=brand,
)

check("the owner changes their password", changed, 200)

# Changing a password ends every session, this one included -
# which is the behaviour, not a problem. The endpoint hands back
# a replacement so the person is not signed out of the browser
# they just used, and anything carrying on here has to take it.
if changed.status_code == 200:
    brand = {
        "Authorization": f"Bearer {changed.json()['access_token']}"
    }

if queued_for(BRAND, NotificationKind.PASSWORD_CHANGED) == 1:
    ok("and is told, despite having switched things off")
else:
    bad("no email about a password change")

print()
print("=" * 62)
print("The message nudge waits, and usually never goes")
print("=" * 62)

clear_outbox()

sent = client.post(
    "/conversations/messages",
    json={"to_workspace_id": creator_ws, "body": "Are you free?"},
    headers=brand,
)

check("the agency messages the creator", sent, 201)

nudges = outbox(NotificationKind.MESSAGE_REQUEST) + outbox(
    NotificationKind.UNREAD_MESSAGES
)

if len(nudges) == 1 and nudges[0].to_email == CREATOR:
    ok("one nudge is queued for the creator")
else:
    bad(
        "the message nudge is wrong",
        str([(n.to_email, n.kind.value) for n in nudges]),
    )

if nudges and nudges[0].send_after > datetime.now(UTC).replace(
    tzinfo=nudges[0].send_after.tzinfo
):
    ok("and it is not due yet - there is a quiet period")
else:
    bad("the nudge was due immediately")

before = len(POSTMAN.sent)
result = drain()

if len(POSTMAN.sent) == before and result["sent"] == 0:
    ok("draining now sends nothing, because nothing is due")
else:
    bad(f"the drain sent something early: {result}")

print()
print("=" * 62)
print("Reading it first means the email is never sent")
print("=" * 62)

conversation_id = sent.json()["id"] if sent.status_code == 201 else None

if conversation_id:
    client.post(
        f"/conversations/{conversation_id}/read",
        headers=creator,
    )

    make_sendable_now()
    result = drain()

    if result["dropped"] >= 1 and result["sent"] == 0:
        ok("a nudge for a thread already read is dropped, not sent")
    else:
        bad(f"the read thread still emailed: {result}")

    dropped = [n for n in outbox() if n.dropped_at is not None]

    if dropped and "read it" in (dropped[0].dropped_reason or ""):
        ok("and the row says why it was not sent")
    else:
        bad(
            "no reason recorded for dropping it",
            str([(n.kind.value, n.dropped_reason) for n in outbox()]),
        )

print()
print("=" * 62)
print("Not reading it means the email is sent, once")
print("=" * 62)

clear_outbox()
POSTMAN.sent.clear()

client.post(
    "/conversations/messages",
    json={
        "conversation_id": conversation_id,
        "body": "Still interested?",
    },
    headers=brand,
)

make_sendable_now()
result = drain()

if result["sent"] == 1 and len(POSTMAN.sent) == 1:
    ok("an unread thread does get an email")
else:
    bad(f"the unread nudge did not send: {result}")

if POSTMAN.sent and POSTMAN.sent[0].to == CREATOR:
    ok(f'addressed to the creator: "{POSTMAN.sent[0].subject}"')
else:
    bad("sent to the wrong person")

if POSTMAN.sent and "TalentX" in POSTMAN.sent[0].subject:
    ok("and it says who it is from")
else:
    bad(
        "the subject does not name the sender",
        POSTMAN.sent[0].subject if POSTMAN.sent else "",
    )

# Draining again must not send it twice.
again = drain()

if again["sent"] == 0 and len(POSTMAN.sent) == 1:
    ok("draining again sends nothing twice")
else:
    bad(f"the drain re-sent an email: {again}")

print()
print("=" * 62)
print("A provider having a day")
print("=" * 62)

clear_outbox()
POSTMAN.sent.clear()
POSTMAN.explode = True

again_changed = client.post(
    "/auth/change-password",
    json={
        "current_password": "An0ther!Passw0rd",
        "new_password": "Third!Passw0rd1",
        "confirm_password": "Third!Passw0rd1",
    },
    headers=brand,
)

if again_changed.status_code == 200:
    brand = {
        "Authorization": (
            f"Bearer {again_changed.json()['access_token']}"
        )
    }

make_sendable_now()
result = drain()

if result["failed"] == 1 and len(POSTMAN.sent) == 0:
    ok("a failed send is counted, not lost")
else:
    bad(f"the failure was not handled: {result}")

rows = [n for n in outbox() if n.sent_at is None]

if rows and rows[0].attempts == 1 and rows[0].last_error:
    ok("the row records the attempt and what went wrong")
else:
    bad(
        "nothing was written about the failure",
        str([(n.attempts, n.last_error) for n in rows]),
    )

# It keeps trying, up to a point.
for _ in range(MAX_ATTEMPTS + 2):
    make_sendable_now()
    drain()

rows = [n for n in outbox() if n.sent_at is None]

if rows and rows[0].attempts == MAX_ATTEMPTS:
    ok(f"it gives up after {MAX_ATTEMPTS} attempts rather than for ever")
else:
    bad(
        "the retry count is wrong",
        str([n.attempts for n in rows]),
    )

# And once the provider is back, a fresh notification goes out -
# the stuck one stays stuck, which is the point of giving up.
POSTMAN.explode = False
make_sendable_now()
recovered = drain()

if recovered["sent"] == 0:
    ok("the given-up row is not picked up again")
else:
    bad(f"a row past its attempts was retried: {recovered}")

print()
print("=" * 62)
print("The address is the one it was queued to")
print("=" * 62)

clear_outbox()
POSTMAN.sent.clear()

fresh = register("mover@notify.example", "Mo")
mover_id = me(fresh)

db = TestSession()
try:
    from app.database.models.user import User

    user = db.get(User, __import__("uuid").UUID(mover_id))
    db.add(
        Notification(
            user_id=user.id,
            to_email=user.email,
            kind=NotificationKind.PASSWORD_CHANGED,
            payload={"when": "now"},
            send_after=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    db.commit()

    # They change their address after it was queued.
    user.email = "moved@notify.example"
    db.commit()
finally:
    db.close()

drain()

if POSTMAN.sent and POSTMAN.sent[0].to == "mover@notify.example":
    ok("mail queued before an address change goes to the old address")
else:
    bad(
        "a queued email followed the address change",
        str([m.to for m in POSTMAN.sent]),
    )

print()
print(f"{len(PASSED)} passed, {len(FAILED)} failed")

if FAILED:
    print()
    for label in FAILED:
        print("  FAILED: " + label)
