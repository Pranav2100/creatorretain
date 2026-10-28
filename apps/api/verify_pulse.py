"""
The pulse: what every open page polls to learn it is stale.

Two properties matter and they pull against each other. It has to
move when something the page shows has changed, or the page sits
there lying. And it has to hold still when nothing has, or every
tab refreshes itself every few seconds for no reason.

So most of this suite is pairs: do a thing, check the scope that
covers it moved, and check the scopes that do not cover it did
not.
"""

import os
import time

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.database.registry  # noqa: F401,E402
from app.database.models.base import Base  # noqa: E402
from app.database.models.content_category import (  # noqa: E402
    ContentCategory,
)

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


def ok(label: str) -> None:
    PASSED.append(label)
    print("PASS  " + label)


def bad(label: str, detail: str = "") -> None:
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
            "password": "Str0ng!Passw0rd",
            "confirm_password": "Str0ng!Passw0rd",
            "first_name": first,
            "last_name": "User",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "Str0ng!Passw0rd"},
    )

    return {"Authorization": f"Bearer {login.json()['access_token']}"}


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

    return r.json()["workspace"]["id"]


def pulse(headers, *scopes, **params):
    query = [("scope", s) for s in scopes] + list(params.items())

    r = client.get("/pulse", params=query, headers=headers)

    assert r.status_code == 200, r.text

    body = r.json()

    # The timestamp alone is not the reading. Two changes inside
    # one clock tick share it, and SQLite's clock is coarse enough
    # that this happens constantly in a test.
    return (body["latest"], body["count"])


def moved(label, before, after):
    if before != after:
        ok(label)
    else:
        bad(label, f"both readings were {before}")


def held(label, before, after):
    if before == after:
        ok(label)
    else:
        bad(label, f"{before} became {after}")


def settle():
    """
    Waits out the clock.

    SQLite stamps updated_at to the nearest second, so two plain
    edits inside the same second are one reading. PostgreSQL does
    not have this problem - it stamps to the microsecond - but a
    suite that only passes on the coarse clock by accident is not
    worth having, so the handful of checks about an edit that
    changes no row count wait first. Inserts and deletes move the
    count and need none of this.
    """
    time.sleep(1.1)


def seed_categories():
    db = TestSession()
    try:
        for slug, name in [("food", "Food"), ("tech", "Tech")]:
            db.add(ContentCategory(slug=slug, name=name))
        db.commit()
    finally:
        db.close()


# ----------------------------------------------------------------------
# The run
# ----------------------------------------------------------------------


def main() -> int:
    seed_categories()

    brand = register("brand@example.com", "Bianca")
    brand_ws = workspace(brand, "Brand Co", "brandco", "brand")
    client.put("/workspace-plan", json={"plan": "pro"}, headers=brand)

    creator = register("creator@example.com", "Cara")
    creator_ws = workspace(
        creator, "Cara Makes", "caramakes", "creator"
    )

    print("--- it answers at all ---")

    check(
        "the pulse needs a session",
        client.get("/pulse", params=[("scope", "retainers")]),
        401,
    )

    check(
        "a signed-in page can read it",
        client.get(
            "/pulse", params=[("scope", "retainers")], headers=brand
        ),
        200,
    )

    check(
        "an unknown scope is refused rather than ignored",
        client.get(
            "/pulse", params=[("scope", "everything")], headers=brand
        ),
        422,
    )

    print("\n--- holding still ---")

    first = pulse(brand, "retainers")
    held("reading it twice changes nothing", first, pulse(brand, "retainers"))

    held(
        "nor does reading it as the other side",
        pulse(creator, "retainers"),
        pulse(creator, "retainers"),
    )

    print("\n--- an offer, and who should hear about it ---")

    before_brand = pulse(brand, "retainers")
    before_creator = pulse(creator, "retainers")
    before_workspace = pulse(brand, "workspace")
    before_profile = pulse(creator, "profile")

    offer = client.post(
        "/retainers",
        json={
            "creator_workspace_id": creator_ws,
            "title": "Monthly content",
            "monthly_amount": "40000.00",
            "deliverables": [{"deliverable_type": "reel", "quantity": 2}],
        },
        headers=brand,
    )
    assert offer.status_code == 201, offer.text
    retainer_id = offer.json()["id"]

    moved(
        "the brand's retainers reading moved",
        before_brand,
        pulse(brand, "retainers"),
    )
    moved(
        "and so did the creator's, without them doing anything",
        before_creator,
        pulse(creator, "retainers"),
    )
    held(
        "but the workspace reading did not",
        before_workspace,
        pulse(brand, "workspace"),
    )
    held(
        "and neither did the profile reading",
        before_profile,
        pulse(creator, "profile"),
    )

    print("\n--- narrowed to one retainer ---")

    one = pulse(brand, "retainers", retainer=retainer_id)

    second = client.post(
        "/retainers",
        json={
            "creator_workspace_id": creator_ws,
            "title": "A second one",
            "monthly_amount": "1000.00",
            "deliverables": [{"deliverable_type": "post", "quantity": 1}],
        },
        headers=brand,
    )

    # The app refuses a second live agreement between the same two,
    # so this asserts the refusal rather than pretending otherwise.
    if second.status_code == 201:
        bad("a second offer to the same creator should be refused")
    else:
        ok("a second offer to the same creator is refused")

    held(
        "watching one retainer ignores the rest of the workspace",
        one,
        pulse(brand, "retainers", retainer=retainer_id),
    )

    print("\n--- every step of the agreement moves it ---")

    steps = [
        (
            "accepting",
            lambda: client.post(
                f"/retainers/{retainer_id}/accept", headers=creator
            ),
        ),
        (
            "asking to pause",
            lambda: client.post(
                f"/retainers/{retainer_id}/requests",
                json={"action": "pause", "reason": "Away."},
                headers=creator,
            ),
        ),
        (
            "agreeing to it",
            lambda: client.post(
                f"/retainers/{retainer_id}/requests/approve",
                headers=brand,
            ),
        ),
        (
            "asking to resume",
            lambda: client.post(
                f"/retainers/{retainer_id}/requests",
                json={"action": "resume"},
                headers=brand,
            ),
        ),
        (
            "saying no to that",
            lambda: client.post(
                f"/retainers/{retainer_id}/requests/reject",
                json={"reason": "Not yet."},
                headers=creator,
            ),
        ),
    ]

    for label, step in steps:
        was = pulse(creator, "retainers", retainer=retainer_id)
        response = step()

        if response.status_code >= 400:
            bad(f"{label} worked", response.text[:160])
            continue

        moved(
            f"{label} moves it for both sides",
            was,
            pulse(creator, "retainers", retainer=retainer_id),
        )

    print("\n--- the team ---")

    was_workspace = pulse(brand, "workspace")
    was_retainers = pulse(brand, "retainers")

    invited = client.post(
        "/workspace-invitations/invite",
        json={"email": "colleague@example.com", "role": "member"},
        headers=brand,
    )

    if invited.status_code >= 400:
        bad("inviting someone worked", invited.text[:160])
    else:
        moved(
            "inviting someone moves the workspace reading",
            was_workspace,
            pulse(brand, "workspace"),
        )
        held(
            "and leaves the retainers reading alone",
            was_retainers,
            pulse(brand, "retainers"),
        )

    settle()
    was_workspace = pulse(brand, "workspace")
    renamed = client.put(
        "/workspaces",
        json={"display_name": "Brand Company"},
        headers=brand,
    )

    if renamed.status_code >= 400:
        bad("renaming the workspace worked", renamed.text[:160])
    else:
        moved(
            "renaming the workspace moves it too",
            was_workspace,
            pulse(brand, "workspace"),
        )

    print("\n--- a creator's own profile ---")

    was_profile = pulse(creator, "profile")
    was_discovery = pulse(brand, "discovery")
    was_workspace = pulse(creator, "workspace")

    edited = client.put(
        "/creator-profile",
        json={"headline": "Food, mostly", "city": "Pune"},
        headers=creator,
    )

    if edited.status_code >= 400:
        bad("editing the profile worked", edited.text[:160])
    else:
        moved(
            "editing a profile moves the profile reading",
            was_profile,
            pulse(creator, "profile"),
        )
        moved(
            "and the discovery reading a brand is watching",
            was_discovery,
            pulse(brand, "discovery"),
        )
        held(
            "but not the workspace reading",
            was_workspace,
            pulse(creator, "workspace"),
        )

    print("\n--- one creator, as a brand watches them ---")

    watched = pulse(brand, "creator", creator=creator_ws)
    other = pulse(brand, "creator", creator=brand_ws)

    # A new row rather than an edit: SQLite's clock has one-second
    # resolution, so two edits in the same second are one reading.
    # The count moves either way, which is exactly why it is here.
    client.post(
        "/creator-profile/portfolio",
        json={"title": "A campaign", "external_url": "https://example.com/x"},
        headers=creator,
    )

    moved(
        "the watched creator's reading moved",
        watched,
        pulse(brand, "creator", creator=creator_ws),
    )
    held(
        "and a different workspace's did not",
        other,
        pulse(brand, "creator", creator=brand_ws),
    )

    empty = pulse(brand, "creator")
    held(
        "the creator scope without a creator is steady, not noisy",
        empty,
        pulse(brand, "creator"),
    )

    print("\n--- several scopes at once ---")

    both = pulse(creator, "profile", "retainers")
    alone = pulse(creator, "profile")

    if both != alone:
        ok("asking for two scopes is not the same as asking for one")
    else:
        bad("asking for two scopes differs from one")

    was_both = pulse(creator, "profile", "retainers")
    client.post(
        "/creator-profile/portfolio",
        json={"title": "Another", "external_url": "https://example.com/y"},
        headers=creator,
    )
    moved(
        "a change in either scope moves the combined reading",
        was_both,
        pulse(creator, "profile", "retainers"),
    )

    repeated = pulse(creator, "profile", "profile")
    once = pulse(creator, "profile")
    if repeated == once:
        ok("a scope repeated by accident is not counted twice")
    else:
        bad(
            "a repeated scope is counted twice",
            f"{repeated} against {once}",
        )

    print("\n--- what one workspace can learn about another ---")

    outsider = register("outsider@example.com", "Otto")
    workspace(outsider, "Outsider", "outsider", "brand")

    theirs = pulse(outsider, "retainers")

    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "resume"},
        headers=brand,
    )

    held(
        "someone else's retainers are invisible here",
        theirs,
        pulse(outsider, "retainers"),
    )

    if theirs[1] == 0:
        ok("a workspace with no retainers reads as empty, not as null")
    else:
        bad("an unrelated workspace sees a count", str(theirs))

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for label in FAILED:
        print("  FAILED:", label)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
