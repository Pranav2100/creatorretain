"""
End-to-end check of the creator profile module.

Runs the real FastAPI app against in-memory SQLite.
"""

import os

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

# The migration seeds these; the metadata-only test schema does not.
CATEGORY_SLUGS = [
    ("food", "Food"),
    ("fashion", "Fashion"),
    ("beauty", "Beauty"),
    ("fitness", "Fitness"),
    ("travel", "Travel"),
    ("tech", "Tech"),
]

_seed = TestSession()
for slug, name in CATEGORY_SLUGS:
    _seed.add(ContentCategory(slug=slug, name=name))
_seed.commit()
_seed.close()

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

PASSED = []
FAILED = []


def check(label, response, expected_status, contains=None):
    ok = response.status_code == expected_status
    if ok and contains:
        ok = contains.lower() in response.text.lower()

    (PASSED if ok else FAILED).append(label)
    print(("PASS  " if ok else "FAIL  ") + label + f"  [{response.status_code}]")
    if not ok:
        print("        expected", expected_status, "got", response.text[:220])
    return response


def note(label):
    PASSED.append(label)
    print("PASS  " + label)


def register(email, first, last):
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Str0ng!Passw0rd",
            "confirm_password": "Str0ng!Passw0rd",
            "first_name": first,
            "last_name": last,
        },
    )
    assert r.status_code in (200, 201), r.text

    login = client.post(
        "/auth/login",
        json={"email": email, "password": "Str0ng!Passw0rd"},
    )
    assert login.status_code == 200, login.text

    return {"Authorization": f"Bearer {login.json()['access_token']}"}


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


def main():
    priya = register("priya@test.com", "Priya", "Sharma")
    make_workspace(priya, "Priya Cooks", "priyacooks", "creator")

    agency = register("agency@test.com", "Ana", "Agent")
    make_workspace(agency, "Acme Agency", "acmeagency", "agency")

    rival = register("rival@test.com", "Rival", "Creator")
    make_workspace(rival, "Rival Media", "rivalmedia", "creator")

    print("\n--- access ---")
    check(
        "agency workspace has no creator profile",
        client.get("/creator-profile/me", headers=agency),
        403,
        "creator workspaces",
    )

    r = check(
        "creator gets an empty draft profile",
        client.get("/creator-profile/me", headers=priya),
        200,
    )
    profile = r.json()
    assert profile["status"] == "draft", profile
    assert profile["completeness"] == 0, profile
    assert profile["is_discoverable"] is False, profile
    assert set(profile["missing_fields"]) == {
        "headline",
        "bio",
        "location",
        "languages",
        "categories",
        "social",
        "pricing",
    }, profile["missing_fields"]
    note("empty profile lists every missing field")

    print("\n--- categories ---")
    categories = client.get("/content-categories").json()["categories"]
    assert len(categories) == 6, categories
    note(f"category reference list is public ({len(categories)} seeded)")

    check(
        "more than five categories is rejected",
        client.put(
            "/creator-profile/categories",
            json={"category_ids": [c["id"] for c in categories]},
            headers=priya,
        ),
        422,
    )

    r = check(
        "five categories accepted",
        client.put(
            "/creator-profile/categories",
            json={
                "category_ids": [c["id"] for c in categories[:5]]
            },
            headers=priya,
        ),
        200,
    )
    assert len(r.json()["categories"]) == 5, r.json()

    print("\n--- basics ---")
    r = check(
        "profile basics saved",
        client.put(
            "/creator-profile",
            json={
                "headline": "Food creator, Pune",
                "bio": "Home cooking, street food, restaurant reviews.",
                "city": "Pune",
                "country": "IN",
                "languages": ["en", "hi", "mr"],
                "skills": ["editing", "food styling"],
                "availability": "available",
            },
            headers=priya,
        ),
        200,
    )
    profile = r.json()
    assert profile["completeness"] == 55, profile["completeness"]
    assert profile["status"] == "draft", profile
    assert set(profile["missing_fields"]) == {"social", "pricing"}, profile[
        "missing_fields"
    ]
    note("completeness rises to 55, still draft, two fields missing")

    print("\n--- social accounts ---")
    r = check(
        "instagram account added",
        client.post(
            "/creator-profile/social-accounts",
            json={
                "platform": "instagram",
                "handle": "@priyacooks",
                "claimed_followers": 48200,
                "claimed_engagement_rate": "4.30",
            },
            headers=priya,
        ),
        201,
    )
    account = r.json()
    assert account["handle"] == "priyacooks", account
    assert account["verified_followers"] is None, account
    assert account["is_verified"] is False, account
    note("handle stored without the @, verified fields left null")

    check(
        "a second instagram account is rejected",
        client.post(
            "/creator-profile/social-accounts",
            json={
                "platform": "instagram",
                "handle": "otherhandle",
                "claimed_followers": 100,
            },
            headers=priya,
        ),
        409,
        "already linked",
    )

    print("\n--- rates and publishing ---")
    r = check(
        "rate added in rupees",
        client.post(
            "/creator-profile/rates",
            json={
                "deliverable_type": "reel",
                "quantity": 5,
                "price": "42500.00",
                "currency": "INR",
            },
            headers=priya,
        ),
        201,
    )
    assert r.json()["price"] == "42500.00", r.json()
    note("price stored exactly as 42500.00, not a float")

    r = client.get("/creator-profile/me", headers=priya)
    profile = r.json()
    assert profile["status"] == "published", profile
    assert profile["is_discoverable"] is True, profile
    assert profile["missing_fields"] == [], profile
    assert profile["completeness"] == 95, profile["completeness"]
    note("profile publishes itself once everything required is present")

    print("\n--- portfolio ---")
    for title in ("Street food series", "Diwali sweets"):
        client.post(
            "/creator-profile/portfolio",
            json={
                "title": title,
                "platform": "instagram",
                "external_url": "https://example.com/post",
            },
            headers=priya,
        )

    profile = client.get(
        "/creator-profile/me", headers=priya
    ).json()
    positions = [i["position"] for i in profile["portfolio_items"]]
    assert positions == [0, 1], positions
    assert profile["completeness"] == 100, profile["completeness"]
    note("portfolio positions increment, completeness reaches 100")

    print("\n--- visibility ---")
    r = check(
        "creator can hide a published profile",
        client.patch(
            "/creator-profile/visibility",
            json={"is_hidden": True},
            headers=priya,
        ),
        200,
    )
    hidden = r.json()
    assert hidden["status"] == "published", hidden
    assert hidden["is_discoverable"] is False, hidden
    note("hiding does not unpublish, only removes it from discovery")

    client.patch(
        "/creator-profile/visibility",
        json={"is_hidden": False},
        headers=priya,
    )

    print("\n--- publishing reverses ---")
    account_id = profile["social_accounts"][0]["id"]
    check(
        "social account removed",
        client.delete(
            f"/creator-profile/social-accounts/{account_id}",
            headers=priya,
        ),
        200,
    )

    reverted = client.get(
        "/creator-profile/me", headers=priya
    ).json()
    assert reverted["status"] == "draft", reverted
    assert reverted["missing_fields"] == ["social"], reverted
    note("removing a required field returns the profile to draft")

    client.post(
        "/creator-profile/social-accounts",
        json={
            "platform": "instagram",
            "handle": "priyacooks",
            "claimed_followers": 48200,
        },
        headers=priya,
    )

    print("\n--- ownership ---")
    rate_id = client.get(
        "/creator-profile/me", headers=priya
    ).json()["rates"][0]["id"]

    check(
        "another creator cannot edit this rate",
        client.patch(
            f"/creator-profile/rates/{rate_id}",
            json={"price": "1.00"},
            headers=rival,
        ),
        404,
    )

    check(
        "another creator cannot delete this rate",
        client.delete(
            f"/creator-profile/rates/{rate_id}",
            headers=rival,
        ),
        404,
    )

    check(
        "a zero rate is rejected",
        client.post(
            "/creator-profile/rates",
            json={"deliverable_type": "post", "price": "0"},
            headers=priya,
        ),
        422,
    )

    rival_profile = client.get(
        "/creator-profile/me", headers=rival
    ).json()
    assert rival_profile["rates"] == [], rival_profile
    assert rival_profile["status"] == "draft", rival_profile
    note("the second creator's profile is untouched")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  FAILED:", f)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
