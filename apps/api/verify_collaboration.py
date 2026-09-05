"""
End-to-end check of the collaboration flow.

Runs the real FastAPI app against an in-memory SQLite database so the
whole Owner/Admin/Member matrix can be exercised without Supabase.
"""

import os
from datetime import datetime

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database.models.base import Base  # noqa: E402
import app.database.registry  # noqa: F401,E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

# SQLite drops tzinfo on read, so keep both sides of the expiry
# comparison naive inside the harness.
import app.services.workspace_invitation as inv_module  # noqa: E402


class _Naive(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.utcnow()


inv_module.datetime = _Naive

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

    (PASSED if ok else FAILED).append(
        f"{label} -> {response.status_code} {response.text[:160]}"
    )
    print(("PASS  " if ok else "FAIL  ") + label + f"  [{response.status_code}]")
    if not ok:
        print("        expected", expected_status, "got", response.text[:200])
    return response


def register(email, first="Test", last="User"):
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
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def main():
    owner = register("owner@test.com", "Olivia", "Owner")
    alice = register("alice@test.com", "Alice", "Admin")
    bob = register("bob@test.com", "Bob", "Member")
    carol = register("carol@test.com", "Carol", "Creator")

    print("\n--- workspace setup ---")
    check(
        "owner creates agency workspace",
        client.post(
            "/workspaces",
            json={
                "display_name": "Acme Agency",
                "username": "acmeagency",
                "workspace_type": "agency",
            },
            headers=owner,
        ),
        201,
    )

    check(
        "creator creates creator workspace",
        client.post(
            "/workspaces",
            json={
                "display_name": "Carol Creates",
                "username": "carolcreates",
                "workspace_type": "creator",
            },
            headers=carol,
        ),
        201,
    )

    check(
        "creator workspace cannot invite",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "bob@test.com", "role": "member"},
            headers=carol,
        ),
        403,
        "creator workspaces cannot invite",
    )

    print("\n--- invite and accept ---")
    check(
        "owner invites alice",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "alice@test.com", "role": "member"},
            headers=owner,
        ),
        200,
    )

    invitation_id = client.get(
        "/workspace-invitations", headers=alice
    ).json()["invitations"][0]["id"]

    check(
        "alice accepts",
        client.post(
            f"/workspace-invitations/{invitation_id}/accept",
            headers=alice,
        ),
        200,
    )

    print("\n--- list members ---")
    r = check("owner lists members", client.get("/workspace-members", headers=owner), 200)
    members = r.json()["members"]
    assert len(members) == 2, members
    assert members[0]["role"] == "owner", members
    assert members[0]["email"] == "owner@test.com", members

    check(
        "member cannot list members",
        client.get("/workspace-members", headers=alice),
        403,
    )

    check(
        "member sees workspace via /workspaces/me",
        client.get("/workspaces/me", headers=alice),
        200,
        "acmeagency",
    )

    alice_member_id = next(
        m["id"] for m in members if m["email"] == "alice@test.com"
    )

    print("\n--- role changes ---")
    check(
        "member cannot change roles",
        client.patch(
            f"/workspace-members/{alice_member_id}/role",
            json={"role": "admin"},
            headers=alice,
        ),
        403,
    )

    check(
        "owner promotes alice to admin",
        client.patch(
            f"/workspace-members/{alice_member_id}/role",
            json={"role": "admin"},
            headers=owner,
        ),
        200,
    )

    check(
        "admin can now list members",
        client.get("/workspace-members", headers=alice),
        200,
    )

    print("\n--- admin invites ---")
    check(
        "admin invites bob",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "bob@test.com", "role": "member"},
            headers=alice,
        ),
        200,
    )

    bob_invitation = client.get(
        "/workspace-invitations", headers=bob
    ).json()["invitations"][0]["id"]

    check(
        "bob accepts",
        client.post(
            f"/workspace-invitations/{bob_invitation}/accept",
            headers=bob,
        ),
        200,
    )

    members = client.get("/workspace-members", headers=owner).json()["members"]
    bob_member_id = next(m["id"] for m in members if m["email"] == "bob@test.com")
    owner_member_id = next(
        m["id"] for m in members if m["email"] == "owner@test.com"
    )

    print("\n--- admin boundaries ---")
    check(
        "admin promotes bob to admin",
        client.patch(
            f"/workspace-members/{bob_member_id}/role",
            json={"role": "admin"},
            headers=alice,
        ),
        200,
    )

    check(
        "admin cannot demote another admin",
        client.patch(
            f"/workspace-members/{bob_member_id}/role",
            json={"role": "member"},
            headers=alice,
        ),
        403,
    )

    check(
        "admin cannot remove another admin",
        client.delete(
            f"/workspace-members/{bob_member_id}", headers=alice
        ),
        403,
    )

    check(
        "admin cannot remove the owner",
        client.delete(
            f"/workspace-members/{owner_member_id}", headers=alice
        ),
        403,
    )

    check(
        "owner demotes bob back to member",
        client.patch(
            f"/workspace-members/{bob_member_id}/role",
            json={"role": "member"},
            headers=owner,
        ),
        200,
    )

    check(
        "admin removes regular member",
        client.delete(f"/workspace-members/{bob_member_id}", headers=alice),
        200,
    )

    print("\n--- re-invite a removed member ---")
    check(
        "owner re-invites bob",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "bob@test.com", "role": "member"},
            headers=owner,
        ),
        200,
    )

    bob_invitation = client.get(
        "/workspace-invitations", headers=bob
    ).json()["invitations"][0]["id"]

    check(
        "bob re-accepts (row reactivated, no unique violation)",
        client.post(
            f"/workspace-invitations/{bob_invitation}/accept",
            headers=bob,
        ),
        200,
    )

    print("\n--- leaving ---")
    check(
        "member leaves",
        client.post("/workspace-members/leave", headers=bob),
        200,
    )

    check(
        "owner cannot leave",
        client.post("/workspace-members/leave", headers=owner),
        409,
        "transfer ownership",
    )

    print("\n--- ownership transfer ---")
    check(
        "admin cannot transfer ownership",
        client.post(
            f"/workspace-members/{alice_member_id}/transfer-ownership",
            headers=alice,
        ),
        403,
    )

    check(
        "owner transfers ownership to alice",
        client.post(
            f"/workspace-members/{alice_member_id}/transfer-ownership",
            headers=owner,
        ),
        200,
    )

    members = client.get("/workspace-members", headers=alice).json()["members"]
    roles = {m["email"]: m["role"] for m in members}
    assert roles["alice@test.com"] == "owner", roles
    assert roles["owner@test.com"] == "admin", roles
    print("PASS  roles after transfer:", roles)

    workspace = client.get("/workspaces/me", headers=alice).json()
    alice_user_id = next(
        m["user_id"] for m in members if m["email"] == "alice@test.com"
    )
    assert workspace["owner_user_id"] == alice_user_id, workspace
    print("PASS  workspaces.owner_user_id updated")

    check(
        "old owner (now admin) can leave",
        client.post("/workspace-members/leave", headers=owner),
        200,
    )

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    for f in FAILED:
        print("  FAILED:", f)
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
