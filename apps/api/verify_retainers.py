"""
End-to-end check of retainers.

Runs the real FastAPI app against in-memory SQLite.

The interesting part is time. A retainer's months are derived, not
stored in advance, so the suite moves the clock forward and asks
the app what it thinks exists - which is the only honest way to
test something that is supposed to happen next month.
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from datetime import date, timedelta  # noqa: E402

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

_seed = TestSession()
for slug, name in [("food", "Food"), ("tech", "Tech")]:
    _seed.add(ContentCategory(slug=slug, name=name))
_seed.commit()
_seed.close()

# SQLite drops tzinfo on read, so the invitation expiry check - used
# here only to put a Member in the workspace - needs both sides of
# its comparison naive. Same shim as verify_collaboration.
import app.database.models.workspace_invitation as _inv_model  # noqa: E402
import app.database.repositories.workspace_invitation as _inv_repo  # noqa: E402
import app.services.workspace_invitation as _inv_service  # noqa: E402
from datetime import datetime as _datetime  # noqa: E402


class _Naive(_datetime):
    @classmethod
    def now(cls, tz=None):
        return _datetime.now()


_inv_service.datetime = _Naive
_inv_model.datetime = _Naive
_inv_repo.datetime = _Naive

import app.api.dependencies.services as _services  # noqa: E402
from app.services.email.base import EmailSender  # noqa: E402


class _Silent(EmailSender):
    def send(self, message):
        pass


_services.get_email_sender = lambda: _Silent()

from fastapi.testclient import TestClient  # noqa: E402

from app.database.repositories.retainer import (  # noqa: E402
    RetainerRepository,
)
from app.database.repositories.workspace import (  # noqa: E402
    WorkspaceRepository,
)
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.retainer import RetainerService  # noqa: E402

# ----------------------------------------------------------------------
# A clock the suite can move
# ----------------------------------------------------------------------

TODAY = date(2026, 10, 12)


def now() -> date:
    return TODAY


def travel_to(day: date) -> None:
    global TODAY
    TODAY = day


def retainer_service(db):
    return RetainerService(
        repository=RetainerRepository(db),
        workspace_repository=WorkspaceRepository(db),
        member_service=_services.get_workspace_member_service(db),
        clock=now,
    )


def override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


def override_retainer_service():
    """
    The same service the app builds, with the suite's clock in
    place of the real one. Nothing else about it changes.
    """
    return retainer_service(TestSession())


app.dependency_overrides[get_db] = override_db
app.dependency_overrides[_services.get_retainer_service] = (
    override_retainer_service
)

client = TestClient(app)

PASSED = []
FAILED = []


def check(label, response, expected_status, contains=None):
    ok = response.status_code == expected_status

    if ok and contains:
        ok = contains.lower() in response.text.lower()

    (PASSED if ok else FAILED).append(label)
    print(
        ("PASS  " if ok else "FAIL  ")
        + label
        + f"  [{response.status_code}]"
    )

    if not ok:
        print(
            "        expected",
            expected_status,
            "got",
            response.text[:300],
        )

    return response


def note(label):
    PASSED.append(label)
    print("PASS  " + label)


def register(email):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Str0ng!Passw0rd",
            "confirm_password": "Str0ng!Passw0rd",
            "first_name": email.split("@")[0].title(),
            "last_name": "Test",
        },
    )

    login = client.post(
        "/auth/login",
        json={"email": email, "password": "Str0ng!Passw0rd"},
    )
    assert login.status_code == 200, login.text

    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }

    # Joining someone else's workspace needs a job title and a
    # phone number, because a creator on the far side of an offer
    # is shown both. Filled in here so these checks stay about
    # retainers; the gate itself is checked in
    # verify_collaboration.
    client.patch(
        "/auth/me",
        json={"job_title": "Talent Manager", "phone": "+919876543210"},
        headers=headers,
    )

    return headers


def make_workspace(headers, name, username, kind):
    r = client.post(
        "/workspaces",
        json={
            "display_name": name,
            "username": username,
            "workspace_type": kind,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    return r.json()["workspace"]["id"]


def upgrade(headers, plan="pro"):
    r = client.put(
        "/workspace-plan",
        json={"plan": plan},
        headers=headers,
    )
    assert r.status_code == 200, r.text


def build_creator(email, username, display_name):
    headers = register(email)
    workspace_id = make_workspace(
        headers,
        display_name,
        username,
        "creator",
    )

    categories = client.get("/content-categories").json()[
        "categories"
    ]

    client.put(
        "/creator-profile/categories",
        json={"category_ids": [categories[0]["id"]]},
        headers=headers,
    )

    client.put(
        "/creator-profile",
        json={
            "headline": f"{display_name} creator",
            "bio": "A bio long enough to be real.",
            "city": "Pune",
            "country": "IN",
            "languages": ["en"],
            "monthly_retainer_min": "30000.00",
            "availability": "available",
        },
        headers=headers,
    )

    client.post(
        "/creator-profile/social-accounts",
        json={
            "platform": "instagram",
            "handle": username,
            "claimed_followers": 50_000,
            "claimed_engagement_rate": "4.00",
        },
        headers=headers,
    )

    return headers, workspace_id


def offer(headers, creator_workspace_id, **overrides):
    body = {
        "creator_workspace_id": creator_workspace_id,
        "title": "Monthly content",
        "monthly_amount": "40000.00",
        "deliverables": [
            {"deliverable_type": "reel", "quantity": 4},
            {"deliverable_type": "story", "quantity": 2},
        ],
    }
    body.update(overrides)

    return client.post("/retainers", json=body, headers=headers)


def main():
    print("--- the cast ---")

    brand = register("brand@test.com")
    make_workspace(brand, "Acme Drinks", "acmedrinks", "brand")

    nina, nina_workspace = build_creator(
        "nina@test.com",
        "ninacooks",
        "Nina Cooks",
    )
    raj, raj_workspace = build_creator(
        "raj@test.com",
        "rajeats",
        "Raj Eats",
    )

    note("a brand and two creators exist")

    print("\n--- the plan gate ---")

    r = check(
        "a Free brand cannot create a retainer",
        offer(brand, nina_workspace),
        402,
    )
    assert "pro" in r.text.lower(), r.text
    note("the refusal names the tier that unlocks it")

    upgrade(brand, "pro")

    print("\n--- sending an offer ---")

    r = check(
        "a Pro brand offers a retainer",
        offer(brand, nina_workspace),
        201,
    )

    body = r.json()
    retainer_id = body["id"]

    assert body["status"] == "pending", body
    assert body["periods"] == [], body
    assert body["your_side"] == "brand", body
    note("a pending offer has no periods - nothing is owed yet")

    assert body["anchor_day"] == 12, body
    note("the anchor day comes from the start date")

    print("\n--- who the creator is actually dealing with ---")

    seen = client.get(
        f"/retainers/{retainer_id}", headers=nina
    ).json()

    contact = seen["contact"]

    if contact is None:
        bad("the creator is told who sent the offer", str(seen)[:200])
    else:
        assert contact["name"] == "Brand Test", contact
        assert contact["job_title"] == "Talent Manager", contact
        assert contact["email"] == "brand@test.com", contact
        assert contact["phone"], contact
        note("a name, a title and a way to reach them, not just a company")

    mine = client.get(
        f"/retainers/{retainer_id}", headers=brand
    ).json()

    if mine["contact"] == contact:
        note("the sender sees the same record, from their own side")
    else:
        bad("both sides read the same contact")

    check(
        "the same creator cannot be offered twice at once",
        offer(brand, nina_workspace),
        409,
        "already have a live retainer",
    )

    check(
        "a brand cannot put itself on retainer",
        offer(brand, body["brand"]["workspace_id"]),
        409,
        "own workspace",
    )

    rival = register("rival@test.com")
    rival_workspace = make_workspace(
        rival,
        "Rival Drinks",
        "rivaldrinks",
        "brand",
    )

    check(
        "a retainer cannot be offered to another brand",
        offer(brand, rival_workspace),
        409,
        "only be offered to creators",
    )

    r = check(
        "a retainer needs at least one deliverable",
        offer(brand, raj_workspace, deliverables=[]),
        422,
    )

    check(
        "the same deliverable cannot be listed twice",
        offer(
            brand,
            raj_workspace,
            deliverables=[
                {"deliverable_type": "reel", "quantity": 2},
                {"deliverable_type": "reel", "quantity": 3},
            ],
        ),
        409,
        "listed twice",
    )

    print("\n--- who can see it ---")

    outsider, _ = build_creator(
        "zoe@test.com",
        "zoeparent",
        "Zoe Parent",
    )

    check(
        "an unrelated workspace gets a 404, not a 403",
        client.get(f"/retainers/{retainer_id}", headers=outsider),
        404,
    )
    note("a stranger is not told the retainer exists")

    r = client.get(f"/retainers/{retainer_id}", headers=nina)
    assert r.status_code == 200, r.text
    assert r.json()["your_side"] == "creator", r.json()
    note("the creator sees the same retainer from the other side")

    print("\n--- answering ---")

    check(
        "the brand cannot accept its own offer",
        client.post(
            f"/retainers/{retainer_id}/accept",
            headers=brand,
        ),
        403,
        "only the creator",
    )

    r = check(
        "the creator accepts",
        client.post(
            f"/retainers/{retainer_id}/accept",
            headers=nina,
        ),
        200,
    )

    body = r.json()
    assert body["status"] == "active", body
    assert len(body["periods"]) == 1, body["periods"]

    period = body["periods"][0]
    assert period["sequence"] == 1, period
    assert period["period_start"] == "2026-10-12", period
    assert period["period_end"] == "2026-11-11", period
    assert period["state"] == "current", period
    note("accepting creates month 1 immediately, and only month 1")

    assert len(period["deliverables"]) == 6, period
    reels = [
        d
        for d in period["deliverables"]
        if d["deliverable_type"] == "reel"
    ]
    assert len(reels) == 4, reels
    assert [d["position"] for d in reels] == [1, 2, 3, 4], reels
    note("4 reels and 2 stories become six separate rows")

    assert period["outstanding_count"] == 6, period
    assert period["is_complete"] is False, period
    note("the period knows what is still owed without storing it")

    check(
        "a second accept is refused",
        client.post(
            f"/retainers/{retainer_id}/accept",
            headers=nina,
        ),
        409,
    )

    check(
        "an answered offer cannot be withdrawn",
        client.post(
            f"/retainers/{retainer_id}/cancel",
            headers=brand,
        ),
        409,
        "already been answered",
    )

    print("\n--- time passes ---")

    travel_to(date(2026, 11, 11))

    r = client.get(f"/retainers/{retainer_id}/periods", headers=brand)
    assert r.json()["total"] == 1, r.json()
    note("the day before renewal, still one month")

    travel_to(date(2026, 11, 12))

    r = client.get(f"/retainers/{retainer_id}/periods", headers=brand)
    body = r.json()

    assert body["total"] == 2, body
    assert body["periods"][1]["period_start"] == "2026-11-12", body
    assert body["periods"][1]["state"] == "current", body
    assert body["periods"][0]["state"] == "past", body
    note("on the anchor day month 2 appears, month 1 becomes past")

    assert len(body["periods"][1]["deliverables"]) == 6, body
    note("the new month arrives with its own six deliverables")

    r = client.get(f"/retainers/{retainer_id}/periods", headers=brand)
    assert r.json()["total"] == 2, r.json()
    note("asking twice does not create the month twice")

    # A second agreement, left alone for months, so the catch-up
    # case does not disturb the one the rest of the suite uses.
    second = offer(brand, raj_workspace, title="Raj monthly").json()
    client.post(f"/retainers/{second['id']}/accept", headers=raj)

    travel_to(date(2027, 2, 20))

    r = client.get(
        f"/retainers/{second['id']}/periods",
        headers=brand,
    )
    body = r.json()

    assert body["total"] == 4, body["total"]
    assert [p["sequence"] for p in body["periods"]] == [
        1,
        2,
        3,
        4,
    ], body
    assert body["periods"][0]["period_start"] == "2026-11-12", body
    note("untouched for three months, all four appear at once")

    print("\n--- the work ---")

    travel_to(date(2026, 11, 12))

    r = client.get(f"/retainers/{retainer_id}", headers=nina)
    first_month = r.json()["periods"][0]

    shape = [
        (d["deliverable_type"], d["position"])
        for d in first_month["deliverables"]
    ]
    assert shape == [
        ("reel", 1),
        ("reel", 2),
        ("reel", 3),
        ("reel", 4),
        ("story", 1),
        ("story", 2),
    ], shape
    note("deliverables come back grouped by type, in order")

    reel = next(
        d
        for d in first_month["deliverables"]
        if d["deliverable_type"] == "reel" and d["position"] == 1
    )

    check(
        "a url has to be a url",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={"url": "done"},
            headers=nina,
        ),
        422,
    )
    note("the submitted link is validated, not just measured")

    check(
        "the brand cannot submit work",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={"url": "https://example.com/reel-1"},
            headers=brand,
        ),
        403,
        "only the creator",
    )

    r = check(
        "the creator submits a reel",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={
                "url": "https://example.com/reel-1",
                "note": "First cut.",
            },
            headers=nina,
        ),
        200,
    )

    assert r.json()["status"] == "submitted", r.json()
    assert r.json()["submission_count"] == 1, r.json()

    r = check(
        "submitting again before review is the same attempt",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={"url": "https://example.com/reel-1-fixed-typo"},
            headers=nina,
        ),
        200,
    )
    assert r.json()["submission_count"] == 1, r.json()
    note("a double click does not read as a second attempt")

    check(
        "the creator cannot review their own work",
        client.post(
            f"/retainers/deliverables/{reel['id']}/review",
            json={"decision": "approve"},
            headers=nina,
        ),
        403,
        "only the hiring workspace",
    )

    check(
        "a status is not a review decision",
        client.post(
            f"/retainers/deliverables/{reel['id']}/review",
            json={"decision": "pending"},
            headers=brand,
        ),
        422,
    )
    note("the three valid decisions are the only ones offered")

    check(
        "a revision must say what to change",
        client.post(
            f"/retainers/deliverables/{reel['id']}/review",
            json={"decision": "request_revision"},
            headers=brand,
        ),
        409,
        "say what needs changing",
    )

    r = check(
        "the brand asks for a revision",
        client.post(
            f"/retainers/deliverables/{reel['id']}/review",
            json={
                "decision": "request_revision",
                "note": "Cut the intro.",
            },
            headers=brand,
        ),
        200,
    )

    assert r.json()["status"] == "revision_requested", r.json()
    assert r.json()["review_note"] == "Cut the intro.", r.json()

    r = check(
        "the creator resubmits",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={"url": "https://example.com/reel-1-v2"},
            headers=nina,
        ),
        200,
    )

    body = r.json()
    assert body["status"] == "submitted", body
    assert body["submission_count"] == 2, body
    assert body["review_note"] is None, body
    note("resubmitting clears the stale review note")

    r = check(
        "the brand approves",
        client.post(
            f"/retainers/deliverables/{reel['id']}/review",
            json={"decision": "approve"},
            headers=brand,
        ),
        200,
    )
    assert r.json()["status"] == "approved", r.json()

    check(
        "approved work cannot be resubmitted",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={"url": "https://example.com/reel-1-v3"},
            headers=nina,
        ),
        409,
        "already been approved",
    )

    r = client.get(f"/retainers/{retainer_id}", headers=brand)
    month_one = r.json()["periods"][0]
    assert month_one["outstanding_count"] == 5, month_one
    note("approving one of six leaves five outstanding")

    print("\n--- asking to pause ---")

    r = check(
        "asking does not pause anything on its own",
        client.post(
            f"/retainers/{retainer_id}/requests",
            json={"action": "pause", "reason": "Campaign on hold."},
            headers=nina,
        ),
        200,
    )
    body = r.json()
    assert body["status"] == "active", body
    assert body["pending"]["action"] == "pause", body
    assert body["pending"]["by_side"] == "creator", body
    assert body["pending"]["yours"] is True, body
    note("a request is a question, not a change")

    r = client.get(f"/retainers/{retainer_id}", headers=brand)
    assert r.json()["pending"]["yours"] is False, r.json()
    note("the other side sees the same request as not theirs")

    check(
        "the asker cannot approve their own request",
        client.post(
            f"/retainers/{retainer_id}/requests/approve",
            headers=nina,
        ),
        409,
        "you asked for this",
    )

    check(
        "a second request cannot queue behind the first",
        client.post(
            f"/retainers/{retainer_id}/requests",
            json={"action": "pause"},
            headers=brand,
        ),
        409,
        "already a request",
    )

    check(
        "the other side can say no",
        client.post(
            f"/retainers/{retainer_id}/requests/reject",
            json={"reason": "Not yet."},
            headers=brand,
        ),
        200,
    )
    r = client.get(f"/retainers/{retainer_id}", headers=nina)
    assert r.json()["pending"] is None, r.json()
    assert r.json()["status"] == "active", r.json()
    note("rejecting clears the request and changes nothing else")

    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "pause", "reason": "Campaign on hold."},
        headers=nina,
    )

    check(
        "only the asker can withdraw",
        client.delete(
            f"/retainers/{retainer_id}/requests",
            headers=brand,
        ),
        403,
        "not yours to withdraw",
    )

    check(
        "the asker can take it back",
        client.delete(
            f"/retainers/{retainer_id}/requests",
            headers=nina,
        ),
        200,
    )
    assert (
        client.get(f"/retainers/{retainer_id}", headers=nina).json()[
            "pending"
        ]
        is None
    )

    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "pause", "reason": "Campaign on hold."},
        headers=nina,
    )

    r = check(
        "the other side approving is what pauses it",
        client.post(
            f"/retainers/{retainer_id}/requests/approve",
            headers=brand,
        ),
        200,
    )
    assert r.json()["status"] == "paused", r.json()
    assert r.json()["pending"] is None, r.json()

    travel_to(date(2027, 1, 20))

    r = client.get(f"/retainers/{retainer_id}/periods", headers=brand)
    assert r.json()["total"] == 2, r.json()
    note("two months pass while paused and no new period appears")

    check(
        "work cannot be submitted on a paused retainer",
        client.post(
            f"/retainers/deliverables/{reel['id']}/submit",
            json={"url": "https://example.com/x"},
            headers=nina,
        ),
        409,
        "not active",
    )

    client.post(
        f"/retainers/{retainer_id}/requests",
        json={"action": "resume"},
        headers=brand,
    )

    r = check(
        "resuming restarts the clock once agreed",
        client.post(
            f"/retainers/{retainer_id}/requests/approve",
            headers=nina,
        ),
        200,
    )

    body = r.json()
    assert body["status"] == "active", body
    assert body["start_date"] == "2027-01-20", body
    assert len(body["periods"]) == 3, body["periods"]

    third = body["periods"][2]
    assert third["sequence"] == 3, third
    assert third["period_start"] == "2027-01-20", third
    note("period 3 starts the day work resumed, not a second month 1")

    travel_to(date(2027, 2, 20))

    r = client.get(f"/retainers/{retainer_id}/periods", headers=brand)
    seqs = [p["sequence"] for p in r.json()["periods"]]
    assert seqs == [1, 2, 3, 4], seqs
    note("numbering carries on across the gap")

    print("\n--- ending serves notice ---")

    # 20 Feb 2027 plus the 30 days agreed at signing.
    r = check(
        "either side can end it",
        client.post(
            f"/retainers/{retainer_id}/end",
            json={"reason": "Budget cut."},
            headers=brand,
        ),
        200,
    )

    body = r.json()
    assert body["status"] == "active", body
    assert body["under_notice"] is True, body
    assert body["end_date"] == "2027-03-22", body
    assert body["notice_given_by_side"] == "brand", body
    assert body["ended_reason"] == "Budget cut.", body
    note("notice given, and it keeps running until it runs out")

    check(
        "nobody has to agree to let the other side leave",
        client.post(
            f"/retainers/{retainer_id}/requests",
            json={"action": "pause"},
            headers=nina,
        ),
        200,
    )
    client.delete(f"/retainers/{retainer_id}/requests", headers=nina)

    check(
        "notice cannot be served twice",
        client.post(
            f"/retainers/{retainer_id}/end",
            headers=brand,
        ),
        409,
        "already been given",
    )

    travel_to(date(2027, 3, 20))
    r = client.get(f"/retainers/{retainer_id}", headers=brand)
    assert r.json()["status"] == "active", r.json()
    note("two days before the date it is still running")

    travel_to(date(2027, 3, 23))
    r = client.get(f"/retainers/{retainer_id}", headers=brand)
    assert r.json()["status"] == "ended", r.json()
    assert r.json()["under_notice"] is False, r.json()
    note("the day after, it reads as ended with nothing having run")

    travel_to(date(2027, 6, 1))

    r = client.get(f"/retainers/{retainer_id}/periods", headers=brand)
    total = r.json()["total"]
    assert total == 5, r.json()
    note("it earned the month inside its notice and then stopped")

    print("\n--- ending with no notice ---")

    travel_to(date(2027, 6, 1))
    quick_headers, quick_id = build_creator(
        "quick@test.com", "quickcreator", "Quick Creator"
    )
    quick = offer(
        brand,
        quick_id,
        title="Short one",
        notice_period_days=0,
    ).json()
    client.post(
        f"/retainers/{quick['id']}/accept",
        headers=quick_headers,
    )

    r = check(
        "zero notice ends it today",
        client.post(
            f"/retainers/{quick['id']}/end",
            json={"reason": "Mutual."},
            headers=brand,
        ),
        200,
    )
    assert r.json()["status"] == "ended", r.json()
    assert r.json()["under_notice"] is False, r.json()

    print("\n--- the plan limit ---")

    travel_to(date(2026, 10, 12))

    limited = register("limited@test.com")
    make_workspace(limited, "Small Brand", "smallbrand", "brand")
    upgrade(limited, "pro")

    creators = []
    for index in range(4):
        _, workspace_id = build_creator(
            f"c{index}@test.com",
            f"creator{index}",
            f"Creator {index}",
        )
        creators.append(workspace_id)

    for index in range(3):
        r = offer(limited, creators[index])
        assert r.status_code == 201, r.text

    r = check(
        "a fourth retainer is refused on Pro",
        offer(limited, creators[3]),
        402,
    )
    assert "3" in r.text, r.text
    note("pending offers count against the ceiling, not just active")

    upgrade(limited, "business")

    check(
        "Business lifts the ceiling",
        offer(limited, creators[3]),
        201,
    )

    print("\n--- roles ---")

    member = register("member@test.com")

    invite = client.post(
        "/workspace-invitations/invite",
        json={"email": "member@test.com", "role": "member"},
        headers=brand,
    )
    assert invite.status_code in (200, 201), invite.text

    pending = client.get(
        "/workspace-invitations",
        headers=member,
    ).json()["invitations"]

    client.post(
        f"/workspace-invitations/{pending[0]['id']}/accept",
        headers=member,
    )

    r = check(
        "a Member can see the workspace's retainers",
        client.get("/retainers", headers=member),
        200,
    )
    assert r.json()["total"] >= 1, r.json()

    check(
        "a Member cannot sign one",
        offer(member, raj_workspace),
        403,
        "owner and admins",
    )
    note("viewing is a Member right, committing money is not")

    print("\n--- listing ---")

    r = client.get(
        "/retainers",
        params={"status": "ended"},
        headers=brand,
    )
    assert r.json()["total"] == 1, r.json()
    note("the list filters by status")

    r = client.get("/retainers", headers=nina)
    body = r.json()
    assert body["total"] == 1, body
    assert body["retainers"][0]["your_side"] == "creator", body
    note("a creator's list shows their side of each agreement")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for failure in FAILED:
        print("  FAILED:", failure)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
