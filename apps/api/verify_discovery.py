"""
End-to-end check of creator discovery.

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

CATEGORIES = [
    ("food", "Food"),
    ("fashion", "Fashion"),
    ("fitness", "Fitness"),
    ("tech", "Tech"),
    ("travel", "Travel"),
]

_seed = TestSession()
for slug, name in CATEGORIES:
    _seed.add(ContentCategory(slug=slug, name=name))
_seed.commit()
_seed.close()

# Console emails would bury the results; invitations are not what
# this suite is testing.
import app.api.dependencies.services as _services  # noqa: E402
from app.services.email.base import EmailSender  # noqa: E402


class _Silent(EmailSender):
    def send(self, message):
        pass


_services.get_email_sender = lambda: _Silent()

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
            response.text[:260],
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


def category_ids(*slugs):
    all_categories = client.get("/content-categories").json()[
        "categories"
    ]
    by_slug = {c["slug"]: c["id"] for c in all_categories}
    return [by_slug[s] for s in slugs]


def build_creator(
    email,
    username,
    display_name,
    *,
    categories,
    followers,
    city="Pune",
    country="IN",
    languages=None,
    engagement="4.00",
    retainer="30000.00",
    platform="instagram",
    publish=True,
):
    headers = register(email)
    make_workspace(headers, display_name, username, "creator")

    client.put(
        "/creator-profile/categories",
        json={"category_ids": category_ids(*categories)},
        headers=headers,
    )

    client.put(
        "/creator-profile",
        json={
            "headline": f"{display_name} creator",
            "bio": "A bio long enough to be real.",
            "city": city,
            "country": country,
            "languages": languages or ["en"],
            "monthly_retainer_min": retainer,
            "availability": "available",
        },
        headers=headers,
    )

    if publish:
        client.post(
            "/creator-profile/social-accounts",
            json={
                "platform": platform,
                "handle": username,
                "claimed_followers": followers,
                "claimed_engagement_rate": engagement,
            },
            headers=headers,
        )

    return headers


def search(headers, **params):
    return client.get(
        "/discovery/creators",
        params=params,
        headers=headers,
    )


def main():
    print("--- building a catalogue ---")

    build_creator(
        "nina@test.com",
        "ninacooks",
        "Nina Cooks",
        categories=["food"],
        followers=120_000,
        languages=["en", "hi"],
        retainer="80000.00",
    )
    build_creator(
        "raj@test.com",
        "rajeats",
        "Raj Eats",
        categories=["food", "travel"],
        followers=45_000,
        city="Mumbai",
        retainer="30000.00",
    )
    build_creator(
        "kim@test.com",
        "kimfit",
        "Kim Fit",
        categories=["fitness"],
        followers=200_000,
        country="US",
        city="Austin",
        retainer="150000.00",
    )
    build_creator(
        "leo@test.com",
        "leotech",
        "Leo Tech",
        categories=["tech"],
        followers=8_000,
        platform="youtube",
        languages=["en", "mr"],
        engagement="9.50",
        retainer="15000.00",
    )
    draft = build_creator(
        "dana@test.com",
        "danadraft",
        "Dana Draft",
        categories=["fashion"],
        followers=0,
        publish=False,
    )

    brand = register("brand@test.com")
    make_workspace(brand, "Acme Drinks", "acmedrinks", "brand")

    r = check(
        "a brand can browse on Free",
        search(brand),
        200,
    )
    body = r.json()
    names = [c["display_name"] for c in body["results"]]

    assert "Dana Draft" not in names, names
    note("an unpublished profile never appears in discovery")

    assert body["total_matching"] == 4, body["total_matching"]
    assert body["can_contact"] is False, body
    note(f"four published creators found, contact locked on Free")

    print("\n--- the result shape ---")

    nina = next(c for c in body["results"] if c["slug"] == "ninacooks")
    assert nina["top_followers"] == 120_000, nina
    assert nina["platforms"][0]["platform"] == "instagram", nina
    assert [c["slug"] for c in nina["categories"]] == ["food"], nina
    assert "bio" not in nina, nina
    note("a card carries reach and categories but not the bio")

    print("\n--- filters ---")

    r = search(brand, category="food")
    assert r.json()["total_matching"] == 2, r.json()
    note("category filter matches two food creators")

    r = search(brand, category=["food", "fitness"])
    assert r.json()["total_matching"] == 3, r.json()
    note("several categories widen rather than narrow")

    r = search(brand, platform="youtube")
    slugs = [c["slug"] for c in r.json()["results"]]
    assert slugs == ["leotech"], slugs
    note("platform filter isolates the YouTube creator")

    r = search(brand, min_followers=100_000)
    assert r.json()["total_matching"] == 2, r.json()
    note("follower floor keeps only the two largest")

    r = search(brand, min_followers=100_000, platform="youtube")
    assert r.json()["total_matching"] == 0, r.json()
    note("reach and platform are matched on the same account, not separately")

    r = search(brand, country="US")
    assert [c["slug"] for c in r.json()["results"]] == ["kimfit"]
    note("country filter works")

    r = search(brand, min_followers=1_000_000)
    body = r.json()
    assert body["total_matching"] == 0 and body["results"] == []
    note("an impossible filter returns an empty set, not an error")

    print("\n--- filters Free cannot use ---")

    r = check(
        "engagement filter is gated",
        search(brand, min_engagement_rate="5.0"),
        402,
        "upgrade to pro",
    )
    assert "engagement rate" in r.text, r.text

    check(
        "city filter is gated",
        search(brand, city="Pune"),
        402,
        "city",
    )

    r = check(
        "several gated filters are named together",
        search(brand, city="Pune", verified_only=True),
        402,
    )
    assert "and" in r.json()["detail"], r.json()
    note("the refusal lists every gated filter in use")

    print("\n--- the Free result cap ---")

    for n in range(9):
        build_creator(
            f"extra{n}@test.com",
            f"extra{n}",
            f"Extra {n}",
            categories=["food"],
            followers=1_000 + n,
        )

    r = search(brand, page_size=50)
    body = r.json()

    assert body["total_matching"] == 13, body["total_matching"]
    assert body["returned"] == 10, body["returned"]
    assert body["result_cap"] == 10, body
    assert body["capped"] is True, body
    note("Free sees 10 of 13 and is told the true total")

    r = search(brand, offset=10, page_size=10)
    body = r.json()
    assert body["returned"] == 0, body
    assert body["total_matching"] == 13, body
    assert body["capped"] is True, body
    note("paging past the cap returns nothing but still reports the total")

    r = search(brand, offset=8, page_size=10)
    assert r.json()["returned"] == 2, r.json()
    note("a page straddling the cap is trimmed to it")

    print("\n--- upgrading ---")

    client.put(
        "/workspace-plan",
        json={"plan": "pro"},
        headers=brand,
    )

    r = search(brand, page_size=50)
    body = r.json()
    assert body["returned"] == 13, body["returned"]
    assert body["result_cap"] is None, body
    assert body["capped"] is False, body
    assert body["can_contact"] is True, body
    note("Pro sees all 13 and can contact")

    r = check(
        "Pro may use the gated filters",
        search(brand, city="Pune", min_engagement_rate="9.0"),
        200,
    )
    assert [c["slug"] for c in r.json()["results"]] == ["leotech"]
    note("engagement and city filters work once unlocked")

    r = search(brand, language="mr")
    assert [c["slug"] for c in r.json()["results"]] == ["leotech"]
    note("language filter matches a secondary language")

    r = search(brand, max_monthly_retainer="20000")
    assert [c["slug"] for c in r.json()["results"]] == ["leotech"]
    note("budget filter keeps only creators within reach")

    print("\n--- ranking ---")

    db = TestSession()
    from datetime import datetime, timedelta

    from app.common.enums import CreatorVerificationStatus
    from app.database.models.creator_profile import CreatorProfile
    from app.database.models.workspace import Workspace

    def profile_for(slug):
        workspace = (
            db.query(Workspace).filter(Workspace.slug == slug).first()
        )
        return (
            db.query(CreatorProfile)
            .filter(CreatorProfile.workspace_id == workspace.id)
            .first()
        )

    # A thin profile with boost bought, against a complete one.
    thin = profile_for("extra0")
    thin.completeness = 60
    thin.boosted_until = datetime.now() + timedelta(days=30)

    complete = profile_for("ninacooks")
    complete.completeness = 100
    complete.verification_status = (
        CreatorVerificationStatus.VERIFIED
    )

    db.add_all([thin, complete])
    db.commit()
    db.close()

    r = search(brand, page_size=50)
    order = [c["slug"] for c in r.json()["results"]]

    assert order.index("ninacooks") < order.index("extra0"), order
    note("a complete verified profile outranks a boosted thin one")

    boosted_card = next(
        c for c in r.json()["results"] if c["slug"] == "extra0"
    )
    assert boosted_card["is_boosted"] is True, boosted_card
    note("boost is visible on the card, so it can be labelled")

    print("\n--- the profile view ---")

    nina_id = next(
        c["id"]
        for c in r.json()["results"]
        if c["slug"] == "ninacooks"
    )

    r = check(
        "a brand opens a creator",
        client.get(f"/discovery/creators/{nina_id}", headers=brand),
        200,
    )
    detail = r.json()
    assert detail["bio"], detail
    assert detail["languages"] == ["en", "hi"], detail
    assert detail["can_contact"] is True, detail
    note("the detail view adds bio, languages and rates")

    check(
        "an unknown creator is a 404",
        client.get(
            "/discovery/creators/"
            "11111111-1111-1111-1111-111111111111",
            headers=brand,
        ),
        404,
    )

    print("\n--- who may browse ---")

    creator = register("nina@test.com")
    r = check(
        "a creator workspace cannot browse discovery",
        search(creator),
        402,
    )
    note("browsing is a brand and agency capability")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  FAILED:", f)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
