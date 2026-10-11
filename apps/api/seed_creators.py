"""
Seed a catalogue of creator profiles for testing discovery.

Writes to whatever DATABASE_URL points at, so this hits the real
Supabase project. It drives the same services the API does rather
than writing rows directly, which means profiles publish through the
real completeness rules and anything that would fail through Swagger
fails here too.

    uv run python seed_creators.py           # create what is missing
    uv run python seed_creators.py --reset   # remove them, then create
    uv run python seed_creators.py --remove  # remove them and stop

Only the accounts listed in CREATORS are ever touched. Nothing else
in the database is read or written.
"""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.common.enums import (
    CreatorAvailability,
    CreatorVerificationStatus,
    SocialPlatform,
    WorkspaceType,
)
from app.database.models.content_category import ContentCategory
from app.database.models.creator_profile import CreatorProfile
from app.database.models.user import User
from app.database.models.workspace_member import WorkspaceMember
from app.database.models.workspace import Workspace
from app.database.repositories.creator_profile import (
    CreatorProfileRepository,
)
from app.database.repositories.user import UserRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.database.session import SessionLocal
from app.schemas.auth import RegisterRequest
from app.schemas.workspace import CreateWorkspaceRequest
from app.services.creator_profile import CreatorProfileService
from app.services.user import UserService
from app.services.workspace import WorkspaceService
from app.services.workspace_member import WorkspaceMemberService

PASSWORD = "Test@123"


# Spread deliberately wide: reach from 5k to 340k, engagement from
# 2.2% to 11.2%, six countries, ten languages and retainers from
# 12,000 to 250,000, so every discovery filter has something to bite
# on and ranking has something to sort.
CREATORS = [
    {
        "email": "nina@test.com",
        "first_name": "Nina",
        "last_name": "Shah",
        "username": "ninacooks",
        "display_name": "Nina Cooks",
        "headline": "Home cooking and street food, Pune",
        "bio": (
            "Everyday Maharashtrian cooking, street food walks and "
            "honest restaurant reviews. Seven years of recipes."
        ),
        "city": "Pune",
        "country": "IN",
        "languages": ["en", "hi", "mr"],
        "skills": ["recipe development", "food styling"],
        "categories": ["food"],
        "retainer": "40000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 48_200,
        "engagement": "4.30",
        "verified": True,
        "rates": [("reel", 1, "9000.00"), ("reel", 5, "40000.00")],
    },
    {
        "email": "raj@test.com",
        "first_name": "Raj",
        "last_name": "Mehta",
        "username": "rajeats",
        "display_name": "Raj Eats",
        "headline": "Food and travel across India",
        "bio": (
            "Eating my way through small towns. Long-form food "
            "travel with a focus on places nobody films."
        ),
        "city": "Mumbai",
        "country": "IN",
        "languages": ["en", "hi", "gu"],
        "skills": ["long form video", "editing"],
        "categories": ["food", "travel"],
        "retainer": "85000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 112_000,
        "engagement": "2.80",
        "rates": [("reel", 1, "18000.00"), ("post", 1, "12000.00")],
    },
    {
        "email": "kim@test.com",
        "first_name": "Kim",
        "last_name": "Park",
        "username": "kimfit",
        "display_name": "Kim Fit",
        "headline": "Strength training for beginners",
        "bio": (
            "Former physiotherapist. Programmes for people who have "
            "never touched a barbell."
        ),
        "city": "Austin",
        "country": "US",
        "languages": ["en", "ko"],
        "skills": ["programming", "form coaching"],
        "categories": ["fitness"],
        "retainer": "250000.00",
        "availability": CreatorAvailability.UNAVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 340_000,
        "engagement": "3.10",
        "rates": [("reel", 1, "60000.00")],
    },
    {
        "email": "leo@test.com",
        "first_name": "Leo",
        "last_name": "Dsouza",
        "username": "leotechtalk",
        "display_name": "Leo Tech Talk",
        "headline": "Developer tools, explained slowly",
        "bio": (
            "Small channel, patient explanations. Mostly backend "
            "tooling and the occasional keyboard."
        ),
        "city": "Bengaluru",
        "country": "IN",
        "languages": ["en", "kn"],
        "skills": ["screencasting", "technical writing"],
        "categories": ["tech", "education"],
        "retainer": "18000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.YOUTUBE,
        "followers": 9_400,
        "engagement": "9.20",
        "boosted": True,
        "rates": [("video", 1, "25000.00")],
    },
    {
        "email": "aisha@test.com",
        "first_name": "Aisha",
        "last_name": "Khan",
        "username": "aishastyles",
        "display_name": "Aisha Styles",
        "headline": "Affordable fashion, Delhi",
        "bio": (
            "Thrift hauls, styling on a budget and the occasional "
            "skincare experiment that goes wrong."
        ),
        "city": "Delhi",
        "country": "IN",
        "languages": ["en", "hi", "ur"],
        "skills": ["styling", "photography"],
        "categories": ["fashion", "beauty"],
        "retainer": "60000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 76_000,
        "engagement": "5.40",
        "rates": [("reel", 1, "14000.00"), ("story", 3, "9000.00")],
    },
    {
        "email": "tara@test.com",
        "first_name": "Tara",
        "last_name": "Iyer",
        "username": "taratravels",
        "display_name": "Tara Travels",
        "headline": "Slow travel, mostly coastal",
        "bio": (
            "One place a month, properly. Goa based, usually "
            "somewhere with a beach and bad wifi."
        ),
        "city": "Panaji",
        "country": "IN",
        "languages": ["en", "ta", "hi"],
        "skills": ["drone", "editing"],
        "categories": ["travel", "lifestyle"],
        "retainer": "25000.00",
        "availability": CreatorAvailability.LIMITED,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 23_000,
        "engagement": "6.80",
        "rates": [("reel", 1, "7000.00")],
    },
    {
        "email": "sam@test.com",
        "first_name": "Sam",
        "last_name": "Rivera",
        "username": "samgames",
        "display_name": "Sam Games",
        "headline": "Indie games, long sessions",
        "bio": (
            "Unhurried playthroughs of games nobody covers. "
            "Spanish and English streams."
        ),
        "city": "Madrid",
        "country": "ES",
        "languages": ["en", "es"],
        "skills": ["streaming", "commentary"],
        "categories": ["gaming"],
        "retainer": "120000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.YOUTUBE,
        "followers": 155_000,
        "engagement": "3.90",
        "rates": [("video", 1, "40000.00")],
    },
    {
        "email": "meera@test.com",
        "first_name": "Meera",
        "last_name": "Joshi",
        "username": "meeraeats",
        "display_name": "Meera Eats",
        "headline": "Nashik food, very small channel",
        "bio": (
            "Tiny audience, very engaged. Regional Maharashtrian "
            "food and vineyard day trips."
        ),
        "city": "Nashik",
        "country": "IN",
        "languages": ["en", "mr", "hi"],
        "skills": ["recipe development"],
        "categories": ["food"],
        "retainer": "12000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 5_100,
        "engagement": "11.20",
        "rates": [("reel", 1, "3500.00")],
    },
    {
        "email": "dev@test.com",
        "first_name": "Dev",
        "last_name": "Patel",
        "username": "devbuilds",
        "display_name": "Dev Builds",
        "headline": "Building things in public",
        "bio": "Weekend projects, shipped and explained.",
        "city": "Pune",
        "country": "IN",
        "languages": ["en", "gu"],
        "skills": ["screencasting"],
        "categories": ["tech"],
        "retainer": "35000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.YOUTUBE,
        "followers": 41_000,
        "engagement": "7.10",
        "rates": [("video", 1, "20000.00")],
    },
    {
        "email": "priya@test.com",
        "first_name": "Priya",
        "last_name": "Nair",
        "username": "priyafit",
        "display_name": "Priya Fit",
        "headline": "Home workouts, no equipment",
        "bio": "Fifteen minute routines for small flats.",
        "city": "Kochi",
        "country": "IN",
        "languages": ["en", "ml", "hi"],
        "skills": ["programming"],
        "categories": ["fitness", "lifestyle"],
        "retainer": "55000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 88_000,
        "engagement": "4.60",
        "rates": [("reel", 1, "13000.00")],
    },
    {
        "email": "omar@test.com",
        "first_name": "Omar",
        "last_name": "Farouk",
        "username": "omarcooks",
        "display_name": "Omar Cooks",
        "headline": "Middle Eastern cooking, Dubai",
        "bio": "Family recipes, filmed properly.",
        "city": "Dubai",
        "country": "AE",
        "languages": ["en", "ar"],
        "skills": ["food styling", "photography"],
        "categories": ["food"],
        "retainer": "180000.00",
        "availability": CreatorAvailability.LIMITED,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 210_000,
        "engagement": "2.20",
        "rates": [("reel", 1, "45000.00")],
    },
    {
        "email": "lily@test.com",
        "first_name": "Lily",
        "last_name": "Chen",
        "username": "lilyart",
        "display_name": "Lily Art",
        "headline": "Watercolour, start to finish",
        "bio": "Unedited painting sessions and supply reviews.",
        "city": "Singapore",
        "country": "SG",
        "languages": ["en", "zh"],
        "skills": ["illustration"],
        "categories": ["art", "education"],
        "retainer": "30000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 31_000,
        "engagement": "8.30",
        "rates": [("post", 1, "8000.00")],
    },
    {
        "email": "arjun@test.com",
        "first_name": "Arjun",
        "last_name": "Rao",
        "username": "arjunmusic",
        "display_name": "Arjun Music",
        "headline": "Carnatic meets everything else",
        "bio": "Fusion arrangements and instrument breakdowns.",
        "city": "Hyderabad",
        "country": "IN",
        "languages": ["en", "te", "hi"],
        "skills": ["composition", "audio editing"],
        "categories": ["music"],
        "retainer": "45000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.YOUTUBE,
        "followers": 67_000,
        "engagement": "5.00",
        "rates": [("video", 1, "22000.00")],
    },
    {
        "email": "zoe@test.com",
        "first_name": "Zoe",
        "last_name": "Martin",
        "username": "zoeparent",
        "display_name": "Zoe Parent",
        "headline": "Parenting, unvarnished",
        "bio": "Two under four. Mostly surviving, sometimes advice.",
        "city": "London",
        "country": "GB",
        "languages": ["en"],
        "skills": ["copywriting"],
        "categories": ["parenting", "lifestyle"],
        "retainer": "22000.00",
        "availability": CreatorAvailability.AVAILABLE,
        "platform": SocialPlatform.INSTAGRAM,
        "followers": 14_000,
        "engagement": "9.90",
        "rates": [("story", 5, "11000.00")],
    },
]

SEED_EMAILS = [c["email"] for c in CREATORS]


def build_services(db):
    member_service = WorkspaceMemberService(
        repository=WorkspaceMemberRepository(db),
        workspace_repository=WorkspaceRepository(db),
    )

    return {
        "user": UserService(UserRepository(db)),
        "workspace": WorkspaceService(
            repository=WorkspaceRepository(db),
            member_service=member_service,
        ),
        "profile": CreatorProfileService(
            repository=CreatorProfileRepository(db),
            member_service=member_service,
        ),
    }


def remove(db) -> int:
    """
    Delete only the seeded accounts, by exact email.

    Deletes in dependency order rather than trusting ON DELETE
    CASCADE. Postgres enforces those constraints and SQLite does not
    unless foreign keys are switched on, so leaning on them leaves
    orphaned profiles behind on some backends and not others.
    """
    users = db.scalars(
        select(User).where(User.email.in_(SEED_EMAILS))
    ).all()

    if not users:
        return 0

    user_ids = [user.id for user in users]

    workspaces = db.scalars(
        select(Workspace).where(
            Workspace.owner_user_id.in_(user_ids)
        )
    ).all()

    workspace_ids = [workspace.id for workspace in workspaces]

    if workspace_ids:
        profiles = db.scalars(
            select(CreatorProfile).where(
                CreatorProfile.workspace_id.in_(workspace_ids)
            )
        ).all()

        # The ORM cascade on CreatorProfile takes its social
        # accounts, portfolio items and rates with it.
        for profile in profiles:
            db.delete(profile)

        members = db.scalars(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id.in_(workspace_ids)
            )
        ).all()

        for member in members:
            db.delete(member)

        db.flush()

        for workspace in workspaces:
            db.delete(workspace)

        db.flush()

    for user in users:
        db.delete(user)

    db.commit()

    return len(users)


def seed_one(db, services, spec) -> str:
    existing = db.scalar(
        select(User).where(User.email == spec["email"])
    )

    if existing is not None:
        return "exists"

    user = services["user"].register(
        RegisterRequest(
            first_name=spec["first_name"],
            last_name=spec["last_name"],
            email=spec["email"],
            password=PASSWORD,
            confirm_password=PASSWORD,
        )
    )

    services["workspace"].create(
        owner_user_id=user.id,
        request=CreateWorkspaceRequest(
            display_name=spec["display_name"],
            username=spec["username"],
            workspace_type=WorkspaceType.CREATOR,
        ),
    )

    categories = (
        db.scalars(
            select(ContentCategory).where(
                ContentCategory.slug.in_(spec["categories"])
            )
        )
        .all()
    )

    services["profile"].set_categories(
        user.id,
        [category.id for category in categories],
    )

    services["profile"].update_basics(
        user.id,
        headline=spec["headline"],
        bio=spec["bio"],
        city=spec["city"],
        country=spec["country"],
        languages=spec["languages"],
        skills=spec["skills"],
        monthly_retainer_min=Decimal(spec["retainer"]),
        availability=spec["availability"],
    )

    services["profile"].add_social_account(
        user.id,
        platform=spec["platform"],
        handle=spec["username"],
        profile_url=(
            f"https://instagram.com/{spec['username']}"
            if spec["platform"] == SocialPlatform.INSTAGRAM
            else f"https://youtube.com/@{spec['username']}"
        ),
        claimed_followers=spec["followers"],
        claimed_engagement_rate=Decimal(spec["engagement"]),
    )

    for deliverable, quantity, price in spec.get("rates", []):
        services["profile"].add_rate(
            user.id,
            deliverable_type=deliverable,
            price=Decimal(price),
            quantity=quantity,
        )

    # Verification and boost are owned by admin review and billing,
    # so there is no service path for them. Set directly, the way
    # those systems eventually will.
    if spec.get("verified") or spec.get("boosted"):
        workspace = db.scalar(
            select(Workspace).where(
                Workspace.slug == spec["username"]
            )
        )
        profile = db.scalar(
            select(CreatorProfile).where(
                CreatorProfile.workspace_id == workspace.id
            )
        )

        if spec.get("verified"):
            profile.verification_status = (
                CreatorVerificationStatus.VERIFIED
            )
            profile.verified_at = datetime.now(timezone.utc)

        if spec.get("boosted"):
            profile.boosted_until = datetime.now(
                timezone.utc
            ) + timedelta(days=30)

        db.add(profile)
        db.commit()

    return "created"


def main() -> int:
    args = set(sys.argv[1:])

    db = SessionLocal()

    try:
        if args & {"--reset", "--remove"}:
            removed = remove(db)
            print(f"Removed {removed} seeded account(s).")

            if "--remove" in args:
                return 0

        services = build_services(db)

        created = 0
        skipped = 0
        published = 0

        for spec in CREATORS:
            try:
                outcome = seed_one(db, services, spec)
            except Exception as error:  # noqa: BLE001
                db.rollback()
                print(f"  FAILED  {spec['username']}: {error}")
                continue

            if outcome == "created":
                created += 1
                print(f"  created {spec['username']}")
            else:
                skipped += 1
                print(f"  exists  {spec['username']}")

        profiles = db.scalars(select(CreatorProfile)).all()
        published = sum(1 for p in profiles if p.is_discoverable)

        print(
            f"\n{created} created, {skipped} already present. "
            f"{published} discoverable profile(s) in total."
        )
        print(f"Every seeded account's password is {PASSWORD}")

        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
