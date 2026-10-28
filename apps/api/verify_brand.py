"""
End-to-end check of the hiring side: editing a workspace, and the
public page a creator reads before accepting an offer.

The interesting part is the track record. Those numbers are counted
from retainers and reviews every time they are asked for, so this
suite sets up real agreements and real review timestamps and then
asks the API what it thinks - rather than trusting a stored
counter, which is the thing the design deliberately avoids.
"""

import base64
import os
import shutil
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

# Uploads go to a throwaway directory, so the suite exercises the
# real store rather than a stub and can then check that the bytes
# actually arrived and later actually went away.
MEDIA_ROOT = tempfile.mkdtemp(prefix="cr-media-")
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_MEDIA_ROOT"] = MEDIA_ROOT

# The smallest valid PNG: one transparent pixel.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

from datetime import datetime, timedelta, timezone  # noqa: E402
from uuid import UUID  # noqa: E402

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

# SQLite drops tzinfo on read, so invitation expiry - used here only
# to put a Member in the workspace - needs both sides of its
# comparison naive. Same shim as verify_collaboration.
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

from app.database.models.retainer import Retainer  # noqa: E402
from app.database.models.retainer_deliverable import (  # noqa: E402
    RetainerDeliverable,
)
from app.database.models.retainer_period import (  # noqa: E402
    RetainerPeriod,
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
    # phone, because the creators that workspace hires are shown
    # both. Filled in here so these checks stay about their own
    # subject; the gate itself is checked in verify_collaboration.
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
        "/workspace-plan", json={"plan": plan}, headers=headers
    )
    assert r.status_code == 200, r.text


def build_creator(email, username, display_name):
    headers = register(email)
    workspace_id = make_workspace(
        headers, display_name, username, "creator"
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
        ],
    }
    body.update(overrides)

    return client.post("/retainers", json=body, headers=headers)


def invite_member(owner_headers, email, role="member"):
    """Puts a second person in the workspace at the given role."""
    r = client.post(
        "/workspace-invitations/invite",
        json={"email": email, "role": role},
        headers=owner_headers,
    )
    assert r.status_code in (200, 201), r.text

    headers = register(email)

    pending = client.get(
        "/workspace-invitations", headers=headers
    ).json()["invitations"]

    invitation_id = next(
        item["id"] for item in pending if item["status"] == "pending"
    )

    accepted = client.post(
        f"/workspace-invitations/{invitation_id}/accept",
        headers=headers,
    )
    assert accepted.status_code == 200, accepted.text

    return headers


def set_review_times(retainer_id, pairs):
    """
    Writes submitted/reviewed timestamps straight onto a retainer's
    deliverables.

    The submit and review endpoints are already covered by
    verify_retainers; what needs proving here is the arithmetic over
    whatever times happen to be in the table, and the only way to
    test a median of specific gaps is to put those gaps there.
    """
    db = TestSession()

    # The id arrives as text out of JSON; the column is a real UUID.
    retainer_id = UUID(str(retainer_id))

    rows = (
        db.query(RetainerDeliverable)
        .join(
            RetainerPeriod,
            RetainerPeriod.id == RetainerDeliverable.period_id,
        )
        .join(Retainer, Retainer.id == RetainerPeriod.retainer_id)
        .filter(Retainer.id == retainer_id)
        .order_by(RetainerDeliverable.position)
        .all()
    )

    base = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)

    assert len(rows) >= len(pairs), (
        f"only {len(rows)} deliverables for {len(pairs)} gaps"
    )

    for index, gap_hours in enumerate(pairs):
        submitted = base + timedelta(days=index)
        rows[index].submitted_at = submitted
        rows[index].reviewed_at = submitted + timedelta(
            hours=gap_hours
        )

    db.commit()
    db.close()


def brand(headers, slug):
    return client.get(f"/brands/{slug}", headers=headers)


def main():
    print("--- editing a workspace ---")

    owner = register("owner@brandcheck.com")
    make_workspace(owner, "TalentX", "talentx", "agency")
    upgrade(owner)

    r = check(
        "owner edits the workspace",
        client.put(
            "/workspaces",
            json={
                "display_name": "TalentX Media",
                "legal_name": "TalentX Media Private Limited",
                "bio": "We put brands on retainer with creators.",
                "website_url": "https://talentx.example",
            },
            headers=owner,
        ),
        200,
    )
    body = r.json()
    assert body["display_name"] == "TalentX Media", body
    # Stored as typed. The URL was checked, not rewritten - nobody
    # wants their address handed back with a slash they did not add.
    assert body["website_url"] == "https://talentx.example", body
    note("name, legal name, bio and website all saved")

    r = check(
        "a field nobody sent is left alone",
        client.put(
            "/workspaces",
            json={"bio": "A shorter bio."},
            headers=owner,
        ),
        200,
    )
    assert r.json()["bio"] == "A shorter bio.", r.json()
    assert (
        r.json()["legal_name"] == "TalentX Media Private Limited"
    ), r.json()
    note("changing the bio did not wipe the registered name")

    r = check(
        "sending null clears the field",
        client.put(
            "/workspaces",
            json={"legal_name": None},
            headers=owner,
        ),
        200,
    )
    assert r.json()["legal_name"] is None, r.json()
    assert r.json()["bio"] == "A shorter bio.", r.json()
    note("a field can actually be emptied, not only overwritten")

    client.put(
        "/workspaces",
        json={"legal_name": "TalentX Media Private Limited"},
        headers=owner,
    )

    check(
        "a name of spaces is refused",
        client.put(
            "/workspaces",
            json={"display_name": "   "},
            headers=owner,
        ),
        400,
        "needs a name",
    )

    check(
        "an explicit null name is refused",
        client.put(
            "/workspaces",
            json={"display_name": None},
            headers=owner,
        ),
        400,
        "needs a name",
    )

    check(
        "something that is not a web address is refused",
        client.put(
            "/workspaces",
            json={"website_url": "my website"},
            headers=owner,
        ),
        422,
        "full web address",
    )

    check(
        "the username cannot be changed here",
        client.put(
            "/workspaces",
            json={"username": "somethingelse"},
            headers=owner,
        ),
        200,
    )
    mine = client.get("/workspaces/me", headers=owner).json()
    assert mine["slug"] == "talentx", mine
    note("an unknown field is ignored rather than moving the slug")

    assert mine["your_role"] == "owner", mine
    note("the workspace says which seat the reader is in")

    print("\n--- uploading a logo ---")

    r = check(
        "a PNG is accepted",
        client.post(
            "/workspaces/logo",
            files={"file": ("logo.png", PNG, "image/png")},
            headers=owner,
        ),
        200,
    )
    first = r.json()["logo_url"]
    assert first and "workspace-logos" in first, r.json()
    note("the stored path is built by us, not from the filename")

    stored = Path(MEDIA_ROOT) / first.split("/media/", 1)[1]
    assert stored.exists(), stored
    note("the bytes really landed in the store")

    r = check(
        "uploading again replaces it",
        client.post(
            "/workspaces/logo",
            files={"file": ("other.png", PNG, "image/png")},
            headers=owner,
        ),
        200,
    )
    second = r.json()["logo_url"]
    assert second != first, second
    assert not stored.exists(), "the old file was left behind"
    note("a new logo gets a new URL and the old file is removed")

    check(
        "an SVG is refused",
        client.post(
            "/workspaces/logo",
            files={
                "file": (
                    "logo.svg",
                    b'<svg xmlns="http://www.w3.org/2000/svg">'
                    b'<script>alert(1)</script></svg>',
                    "image/svg+xml",
                )
            },
            headers=owner,
        ),
        400,
        "svg files are not accepted",
    )
    note("an SVG can carry script, so it never reaches the store")

    check(
        "a file lying about its type is refused",
        client.post(
            "/workspaces/logo",
            files={
                "file": (
                    "totally.png",
                    b"#!/bin/sh\nrm -rf /\n",
                    "image/png",
                )
            },
            headers=owner,
        ),
        400,
        "does not look like an image",
    )
    note("the bytes decide, not the name or the declared type")

    check(
        "an oversized image is refused",
        client.post(
            "/workspaces/logo",
            files={
                "file": (
                    "huge.png",
                    PNG + b"\x00" * (2 * 1024 * 1024),
                    "image/png",
                )
            },
            headers=owner,
        ),
        400,
        "under 2mb",
    )

    check(
        "an empty file is refused",
        client.post(
            "/workspaces/logo",
            files={"file": ("nothing.png", b"", "image/png")},
            headers=owner,
        ),
        400,
        "empty",
    )

    # Everything above was refused, so the good logo should still
    # be exactly where it was.
    assert (
        client.get("/workspaces/me", headers=owner).json()[
            "logo_url"
        ]
        == second
    )
    note("a refused upload leaves the existing logo untouched")

    r = check(
        "the logo can be removed",
        client.delete("/workspaces/logo", headers=owner),
        200,
    )
    assert r.json()["logo_url"] is None, r.json()
    assert not (
        Path(MEDIA_ROOT) / second.split("/media/", 1)[1]
    ).exists()
    note("removing it deletes the file as well as the row")

    check(
        "removing a logo that is not there is fine",
        client.delete("/workspaces/logo", headers=owner),
        200,
    )

    client.post(
        "/workspaces/logo",
        files={"file": ("logo.png", PNG, "image/png")},
        headers=owner,
    )

    print("\n--- who may edit ---")

    member = invite_member(owner, "member@brandcheck.com", "member")
    admin = invite_member(owner, "admin@brandcheck.com", "admin")

    check(
        "a member cannot edit the workspace",
        client.put(
            "/workspaces",
            json={"display_name": "Member Was Here"},
            headers=member,
        ),
        403,
        "owner and admins",
    )

    check(
        "an admin can edit the workspace",
        client.put(
            "/workspaces",
            json={"bio": "Edited by an admin."},
            headers=admin,
        ),
        200,
    )

    assert (
        client.get("/workspaces/me", headers=member).json()[
            "your_role"
        ]
        == "member"
    )
    note("a member is told they are a member, so the UI can say so")

    check(
        "a member cannot upload a logo either",
        client.post(
            "/workspaces/logo",
            files={"file": ("logo.png", PNG, "image/png")},
            headers=member,
        ),
        403,
        "owner and admins",
    )
    note("the upload endpoint checks permission, not just the form")

    check(
        "a member cannot remove the logo",
        client.delete("/workspaces/logo", headers=member),
        403,
    )

    check(
        "someone with no workspace cannot edit one",
        client.put(
            "/workspaces",
            json={"display_name": "Nope"},
            headers=register("nobody@brandcheck.com"),
        ),
        404,
    )

    print("\n--- the public page ---")

    nina, nina_id = build_creator("nina@brandcheck.com", "nina", "Nina")
    raj, raj_id = build_creator("raj@brandcheck.com", "raj", "Raj")
    kim, kim_id = build_creator("kim@brandcheck.com", "kim", "Kim")

    check(
        "an unknown slug is not found",
        brand(nina, "nosuchagency"),
        404,
    )

    check(
        "a creator is not a brand page",
        brand(nina, "nina"),
        404,
        "creator profile",
    )

    r = check(
        "a creator can read the hiring workspace",
        brand(nina, "talentx"),
        200,
    )
    page = r.json()
    assert page["display_name"] == "TalentX Media", page
    assert page["workspace_type"] == "agency", page
    assert page["bio"] == "Edited by an admin.", page
    note("the page shows what the workspace wrote about itself")

    record = page["track_record"]
    assert record["live_retainers"] == 0, record
    assert record["creators_worked_with"] == 0, record
    assert record["typical_review_hours"] is None, record
    assert record["member_since"], record
    note("a brand new agency reports zero, not a flattering blank")

    print("\n--- what the numbers count ---")

    # One accepted, one declined, one left pending.
    accepted = offer(owner, nina_id).json()
    declined = offer(owner, raj_id).json()
    offer(owner, kim_id)

    client.post(f"/retainers/{accepted['id']}/accept", headers=nina)
    client.post(f"/retainers/{declined['id']}/decline", headers=raj)

    record = brand(nina, "talentx").json()["track_record"]
    assert record["live_retainers"] == 1, record
    assert record["creators_worked_with"] == 1, record
    note("a pending offer is not a relationship")
    note("a declined offer is not one either")

    print("\n--- review responsiveness ---")

    record = brand(nina, "talentx").json()["track_record"]
    assert record["typical_review_hours"] is None, record
    assert record["reviews_counted"] == 0, record

    set_review_times(accepted["id"], [10])
    record = brand(nina, "talentx").json()["track_record"]
    assert record["typical_review_hours"] is None, record
    assert record["reviews_counted"] == 1, record
    note("one fast review is not yet a habit worth publishing")

    set_review_times(accepted["id"], [10, 2])
    record = brand(nina, "talentx").json()["track_record"]
    assert record["typical_review_hours"] is None, record
    note("two is still not enough")

    set_review_times(accepted["id"], [2, 10, 6])
    record = brand(nina, "talentx").json()["track_record"]
    assert record["typical_review_hours"] == 6.0, record
    assert record["reviews_counted"] == 3, record
    note("at three it publishes the middle one, 6 hours")

    # The median, not the mean: one abandoned review should not
    # rewrite a record that is otherwise consistent.
    set_review_times(accepted["id"], [2, 3, 4, 500])
    record = brand(nina, "talentx").json()["track_record"]
    assert record["typical_review_hours"] == 3.5, record
    note("one forgotten review does not drag the figure to 127 hours")

    print("\n--- a brand with nothing to hide behind ---")

    quiet = register("quiet@brandcheck.com")
    make_workspace(quiet, "Quiet Co", "quietco", "brand")

    r = check(
        "a brand workspace has a page too",
        brand(nina, "quietco"),
        200,
    )
    page = r.json()
    assert page["workspace_type"] == "brand", page
    assert page["bio"] is None, page
    assert page["track_record"]["live_retainers"] == 0, page
    note("an empty record reads as empty rather than as unknown")

    check(
        "the page needs a signed in reader",
        client.get("/brands/talentx"),
        401,
    )

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for label in FAILED:
        print("  FAILED:", label)

    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
