"""
End-to-end check of the entitlements layer.

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

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSession = sessionmaker(
    bind=engine, autoflush=False, autocommit=False
)
Base.metadata.create_all(engine)

# SQLite drops tzinfo on read, so keep both sides of the invitation
# expiry comparison naive inside the harness. Postgres returns
# timezone-aware values and needs none of this.
from datetime import datetime as _dt  # noqa: E402

import app.database.models.workspace_invitation as _inv_model  # noqa: E402
import app.database.repositories.workspace_invitation as _inv_repo  # noqa: E402
import app.services.workspace_invitation as _inv_service  # noqa: E402


class _Naive(_dt):
    @classmethod
    def now(cls, tz=None):
        return _dt.now()


_inv_model.datetime = _Naive
_inv_repo.datetime = _Naive
_inv_service.datetime = _Naive

from fastapi.testclient import TestClient  # noqa: E402

from app.common.entitlements import (  # noqa: E402
    Capability,
    capabilities_for,
    limits_for,
    plans_for_type,
)
from app.common.enums import (  # noqa: E402
    WorkspacePlan,
    WorkspaceType,
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
            response.text[:220],
        )
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


def set_plan(headers, plan):
    return client.put(
        "/workspace-plan",
        json={"plan": plan},
        headers=headers,
    )


def main():
    print("--- the map itself ---")

    for workspace_type in WorkspaceType:
        for plan in plans_for_type(workspace_type):
            capabilities_for(workspace_type, plan)
            limits_for(workspace_type, plan)
    note("every valid type/plan pair resolves")

    assert WorkspacePlan.BUSINESS not in plans_for_type(
        WorkspaceType.CREATOR
    )
    assert WorkspacePlan.VERIFIED not in plans_for_type(
        WorkspaceType.BRAND
    )
    note("creator plans and brand plans do not bleed into each other")

    free = capabilities_for(WorkspaceType.BRAND, WorkspacePlan.FREE)
    pro = capabilities_for(WorkspaceType.BRAND, WorkspacePlan.PRO)
    business = capabilities_for(
        WorkspaceType.BRAND, WorkspacePlan.BUSINESS
    )
    managed = capabilities_for(
        WorkspaceType.BRAND, WorkspacePlan.MANAGED
    )

    assert free < pro < business < managed, "brand tiers must nest"
    note("brand tiers strictly nest, so upgrading never removes anything")

    # An unknown plan for a type must degrade, not explode.
    orphan = capabilities_for(
        WorkspaceType.CREATOR, WorkspacePlan.MANAGED
    )
    assert orphan == capabilities_for(
        WorkspaceType.CREATOR, WorkspacePlan.FREE
    )
    note("an invalid type/plan pair falls back to Free instead of raising")

    print("\n--- a brand on Free ---")

    brand = register("brand@test.com", "Bea", "Brand")
    make_workspace(brand, "Acme Drinks", "acmedrinks", "brand")

    r = check(
        "new workspace starts on Free",
        client.get("/workspace-plan", headers=brand),
        200,
    )
    plan = r.json()
    assert plan["plan"] == "free", plan
    assert plan["usage"]["team_members"] == 1, plan

    capabilities = set(plan["capabilities"])
    assert Capability.BROWSE_CREATORS in capabilities, capabilities
    assert Capability.CONTACT_CREATOR not in capabilities, capabilities
    note("Free browses creators but cannot contact them")

    assert plan["limits"]["discovery_results"] == 10, plan["limits"]
    note("Free sees 10 discovery results, not the whole catalogue")

    assert plan["limits"]["team_members"] == 10, plan["limits"]

    print("\n--- limits bite ---")

    check(
        "Free brand invites a colleague",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "colleague@test.com", "role": "member"},
            headers=brand,
        ),
        200,
    )

    r = client.get("/workspace-plan", headers=brand).json()
    assert r["usage"]["pending_invitations"] == 1, r["usage"]
    note("a pending invitation holds a seat, so a cap cannot be queued past")

    # Fill the remaining seats to prove the ceiling is real. Free
    # allows 10 and two are already spoken for.
    for n in range(8):
        client.post(
            "/workspace-invitations/invite",
            json={"email": f"seat{n}@test.com", "role": "member"},
            headers=brand,
        )

    r = check(
        "the eleventh seat is refused on Free",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "overflow@test.com", "role": "member"},
            headers=brand,
        ),
        402,
        "upgrade",
    )
    assert "10 team members" in r.text, r.text
    note("the refusal names the ceiling and says to upgrade")

    print("\n--- upgrade ---")

    r = check(
        "owner upgrades to Pro",
        set_plan(brand, "pro"),
        200,
    )
    upgraded = r.json()
    assert upgraded["plan"] == "pro", upgraded
    assert Capability.CONTACT_CREATOR in upgraded["capabilities"]
    assert upgraded["limits"]["team_members"] == 25, upgraded["limits"]
    assert upgraded["limits"]["discovery_results"] is None, upgraded[
        "limits"
    ]
    note("Pro unlocks contact and uncaps discovery")

    check(
        "the overflow seat now goes through",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "overflow@test.com", "role": "member"},
            headers=brand,
        ),
        200,
    )

    check(
        "moving to the plan already held is rejected",
        set_plan(brand, "pro"),
        409,
        "already on",
    )

    check(
        "a brand cannot take a creator plan",
        set_plan(brand, "verified"),
        409,
        "not available",
    )

    print("\n--- downgrade is guarded ---")

    r = check(
        "downgrade below current usage is refused",
        set_plan(brand, "free"),
        409,
        "remove some",
    )
    assert "free allows 10" in r.text.lower(), r.text
    note("the refusal states the ceiling and the current headcount")

    print("\n--- who may change a plan ---")

    colleague = register("colleague@test.com", "Cal", "League")
    invitations = client.get(
        "/workspace-invitations", headers=colleague
    ).json()["invitations"]
    invitation_id = next(
        i["id"] for i in invitations if i["status"] == "pending"
    )
    client.post(
        f"/workspace-invitations/{invitation_id}/accept",
        headers=colleague,
    )

    members = client.get("/workspace-members", headers=brand).json()[
        "members"
    ]
    colleague_member_id = next(
        m["id"]
        for m in members
        if m["email"] == "colleague@test.com"
    )
    client.patch(
        f"/workspace-members/{colleague_member_id}/role",
        json={"role": "admin"},
        headers=brand,
    )

    r = check(
        "an admin cannot change the plan",
        set_plan(colleague, "business"),
        403,
        "only the workspace owner",
    )
    assert "ask them" in r.text.lower(), r.text
    note("paying is an owner decision, not a day-to-day admin one")

    r = check(
        "an admin can still read the plan",
        client.get("/workspace-plan", headers=colleague),
        200,
    )
    assert r.json()["plan"] == "pro", r.json()
    note("everyone in the workspace sees the same plan")

    print("\n--- upgrade screen data ---")

    r = check(
        "plan options list",
        client.get("/workspace-plan/options", headers=brand),
        200,
    )
    options = r.json()["options"]
    assert [o["plan"] for o in options] == [
        "free",
        "pro",
        "business",
        "managed",
    ], options

    current = next(o for o in options if o["is_current"])
    assert current["plan"] == "pro", current
    assert current["adds"] == [], current

    business_option = next(
        o for o in options if o["plan"] == "business"
    )
    assert business_option["adds"] == ["campaign_dashboard"], (
        business_option
    )
    note("each option says what it adds over the plan currently held")

    print("\n--- a creator workspace ---")

    creator = register("creator@test.com", "Cleo", "Creator")
    make_workspace(creator, "Cleo Cooks", "cleocooks", "creator")

    r = client.get("/workspace-plan", headers=creator).json()
    assert r["limits"]["team_members"] == 1, r["limits"]
    assert Capability.PUBLISH_PROFILE in r["capabilities"], r
    assert Capability.CONTACT_CREATOR not in r["capabilities"], r
    note("a creator workspace is a workspace of one, and cannot hire")

    r = check(
        "creator options are only Free and Verified",
        client.get("/workspace-plan/options", headers=creator),
        200,
    )
    assert [o["plan"] for o in r.json()["options"]] == [
        "free",
        "verified",
    ], r.json()

    check(
        "creator upgrades to Verified",
        set_plan(creator, "verified"),
        200,
    )

    r = client.get("/workspace-plan", headers=creator).json()
    assert Capability.VERIFIED_BADGE in r["capabilities"], r
    note("Verified grants the badge capability")

    print("\n--- expiry ---")

    from datetime import datetime, timedelta

    from app.database.models.workspace import Workspace

    db = TestSession()
    workspace = (
        db.query(Workspace)
        .filter(Workspace.slug == "acmedrinks")
        .first()
    )
    workspace.plan_expires_at = datetime.now() - timedelta(days=1)
    db.add(workspace)
    db.commit()
    db.close()

    r = client.get("/workspace-plan", headers=brand).json()
    assert r["plan"] == "free", r
    assert r["configured_plan"] == "pro", r
    assert Capability.CONTACT_CREATOR not in r["capabilities"], r
    note("a lapsed plan reads as Free with no sweep job running")

    check(
        "a lapsed plan loses its capabilities immediately",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "fourth@test.com", "role": "member"},
            headers=brand,
        ),
        402,
    )

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  FAILED:", f)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
