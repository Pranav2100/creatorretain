"""
Four roles, and who can see what.

Two things are being checked and only one of them is about
permissions. The first is the rank matrix: who may promote,
demote and remove whom, now that there is a rung between Admin
and Member.

The second matters more. A Manager sees only the retainers put in
their hands, and "sees" has to mean every way in - the list, the
detail, the months, the history, the work, and the two-number
pulse an open page polls. A filtered list beside an unguarded
detail route is a list that only looks private, because ids turn
up in links, in emails, and in the browser history of whoever had
the account before. So most of this file is one retainer and a
Manager who is not on it, knocking on every door in turn.
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
    """Invites somebody and walks them in."""
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


def offer(headers, creator_workspace_id, title):
    return client.post(
        "/retainers",
        json={
            "creator_workspace_id": creator_workspace_id,
            "title": title,
            "monthly_amount": "40000.00",
            "deliverables": [
                {"deliverable_type": "reel", "quantity": 2}
            ],
        },
        headers=headers,
    )


# ----------------------------------------------------------------------
# The run
# ----------------------------------------------------------------------


def main() -> int:
    seed_categories()

    owner = register("owner@example.com", "Olive")
    workspace(owner, "TalentX", "talentx", "agency")
    client.put("/workspace-plan", json={"plan": "pro"}, headers=owner)

    nina = register("nina@example.com", "Nina")
    nina_ws = workspace(nina, "Nina Cooks", "ninacooks", "creator")

    raj = register("raj@example.com", "Raj")
    raj_ws = workspace(raj, "Raj Eats", "rajeats", "creator")

    print("--- the role exists and can be invited into ---")

    admin = join(owner, "admin@example.com", "admin", "Ada")
    manager = join(owner, "manager@example.com", "manager", "Mira")
    member = join(owner, "member@example.com", "member", "Milo")

    team = client.get("/workspace-members", headers=owner)
    roles = {
        m["email"]: m["role"] for m in team.json()["members"]
    }

    if roles.get("manager@example.com") == "manager":
        ok("somebody can be invited straight in as a manager")
    else:
        bad("a manager can be invited", str(roles))

    check(
        "owner is not an invitable role",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "nope@example.com", "role": "owner"},
            headers=owner,
        ),
        422,
    )

    print("\n--- what a manager may and may not do ---")

    check(
        "a manager can read the team",
        client.get("/workspace-members", headers=manager),
        200,
    )

    check(
        "but cannot invite anybody",
        client.post(
            "/workspace-invitations/invite",
            json={"email": "another@example.com", "role": "member"},
            headers=manager,
        ),
        403,
    )

    check(
        "nor rewrite the page creators read",
        client.put(
            "/workspaces",
            json={"display_name": "Not TalentX"},
            headers=manager,
        ),
        403,
    )

    member_id = me(member)

    check(
        "nor remove anyone",
        client.delete(
            f"/workspace-members/{member_id}", headers=manager
        ),
        403,
    )

    print("\n--- the rank matrix ---")

    manager_member_id = next(
        m["id"]
        for m in team.json()["members"]
        if m["email"] == "manager@example.com"
    )
    member_member_id = next(
        m["id"]
        for m in team.json()["members"]
        if m["email"] == "member@example.com"
    )
    # A second admin, because "an admin cannot touch an admin"
    # has to be tested against somebody else: trying it on
    # yourself is refused for a different reason entirely, and a
    # check that passes for the wrong reason is worse than none.
    other_admin = join(owner, "admin2@example.com", "admin", "Alex")
    assert other_admin is not None

    refreshed = client.get(
        "/workspace-members", headers=owner
    ).json()["members"]

    other_admin_id = next(
        m["id"]
        for m in refreshed
        if m["email"] == "admin2@example.com"
    )

    check(
        "an admin can promote a member to manager",
        client.patch(
            f"/workspace-members/{member_member_id}/role",
            json={"role": "manager"},
            headers=admin,
        ),
        200,
    )

    check(
        "an admin can demote a manager back",
        client.patch(
            f"/workspace-members/{member_member_id}/role",
            json={"role": "member"},
            headers=admin,
        ),
        200,
    )

    check(
        "an admin still cannot touch another admin",
        client.patch(
            f"/workspace-members/{other_admin_id}/role",
            json={"role": "member"},
            headers=admin,
        ),
        403,
    )

    check(
        "nor remove one",
        client.delete(
            f"/workspace-members/{other_admin_id}", headers=admin
        ),
        403,
    )

    check(
        "and nobody changes their own role",
        client.patch(
            f"/workspace-members/{manager_member_id}/role",
            json={"role": "admin"},
            headers=manager,
        ),
        403,
    )

    check(
        "a manager cannot promote anybody",
        client.patch(
            f"/workspace-members/{member_member_id}/role",
            json={"role": "manager"},
            headers=manager,
        ),
        403,
    )

    check(
        "an admin can remove a manager, being senior to one",
        client.delete(
            f"/workspace-members/{manager_member_id}", headers=admin
        ),
        200,
    )

    # Put her back; the rest of this file needs her.
    manager = join(owner, "manager2@example.com", "manager", "Mira")
    manager_id = me(manager)

    print("\n--- a manager sees only what is theirs ---")

    hers = offer(owner, nina_ws, "Nina, monthly").json()
    theirs = offer(owner, raj_ws, "Raj, monthly").json()

    client.post(f"/retainers/{hers['id']}/accept", headers=nina)
    client.post(f"/retainers/{theirs['id']}/accept", headers=raj)

    listed = client.get("/retainers", headers=manager).json()

    if listed["total"] == 0:
        ok("before being assigned, she sees none of them")
    else:
        bad(
            "an unassigned manager sees nothing",
            f"saw {listed['total']}",
        )

    check(
        "the owner still sees both",
        client.get("/retainers", headers=owner),
        200,
    )
    assert (
        client.get("/retainers", headers=owner).json()["total"] == 2
    )

    check(
        "and so does a plain member",
        client.get("/retainers", headers=member),
        200,
    )
    assert (
        client.get("/retainers", headers=member).json()["total"] == 2
    ), "a member watches the whole workspace, they just cannot act"

    print("\n--- putting her on one ---")

    check(
        "a manager cannot assign herself",
        client.post(
            f"/retainers/{hers['id']}/assignees",
            json={"user_id": manager_id},
            headers=manager,
        ),
        404,
        contains="not found",
    )

    assigned = check(
        "the owner puts her on Nina's account",
        client.post(
            f"/retainers/{hers['id']}/assignees",
            json={"user_id": manager_id},
            headers=owner,
        ),
        200,
    )

    if assigned.status_code == 200:
        body = assigned.json()
        assert body["total"] == 1, body
        assert body["assignees"][0]["name"] == "Mira Person", body
        assert body["assignees"][0]["job_title"], body
        ok("who it is and what they do comes back with it")

    check(
        "assigning the same person twice changes nothing",
        client.post(
            f"/retainers/{hers['id']}/assignees",
            json={"user_id": manager_id},
            headers=owner,
        ),
        200,
    )
    assert (
        client.get(
            f"/retainers/{hers['id']}/assignees", headers=owner
        ).json()["total"]
        == 1
    )

    outsider_id = me(nina)

    check(
        "somebody outside the workspace cannot be assigned",
        client.post(
            f"/retainers/{hers['id']}/assignees",
            json={"user_id": outsider_id},
            headers=owner,
        ),
        404,
        contains="not on your team",
    )

    print("\n--- now she sees hers, and only hers ---")

    listed = client.get("/retainers", headers=manager).json()

    if listed["total"] == 1 and listed["retainers"][0]["id"] == hers["id"]:
        ok("the list is the one account she runs")
    else:
        bad("the list shows exactly her account", str(listed)[:200])

    check(
        "she can open it",
        client.get(f"/retainers/{hers['id']}", headers=manager),
        200,
    )

    check(
        "and act on it, which is the point of the role",
        client.post(
            f"/retainers/{hers['id']}/requests",
            json={"action": "pause", "reason": "Away."},
            headers=manager,
        ),
        200,
    )

    client.post(
        f"/retainers/{hers['id']}/requests", headers=manager
    )
    client.delete(
        f"/retainers/{hers['id']}/requests", headers=manager
    )

    print("\n--- every door on the one that is not hers ---")

    other = theirs["id"]

    doors = [
        ("the retainer itself", client.get, f"/retainers/{other}", None),
        ("its months", client.get, f"/retainers/{other}/periods", None),
        ("its history", client.get, f"/retainers/{other}/history", None),
        (
            "who runs it",
            client.get,
            f"/retainers/{other}/assignees",
            None,
        ),
        (
            "asking it to pause",
            client.post,
            f"/retainers/{other}/requests",
            {"action": "pause"},
        ),
        (
            "answering a request on it",
            client.post,
            f"/retainers/{other}/requests/approve",
            None,
        ),
        (
            "giving notice on it",
            client.post,
            f"/retainers/{other}/end",
            {"reason": "No."},
        ),
        (
            "withdrawing the offer",
            client.post,
            f"/retainers/{other}/cancel",
            None,
        ),
    ]

    for label, verb, path, payload in doors:
        response = (
            verb(path, json=payload, headers=manager)
            if payload is not None
            else verb(path, headers=manager)
        )

        if response.status_code == 404:
            ok(f"{label}: not found")
        else:
            bad(
                f"{label}: not found",
                f"[{response.status_code}] {response.text[:160]}",
            )

    # The work hangs off a deliverable id, which is its own door.
    months = client.get(
        f"/retainers/{other}/periods", headers=owner
    ).json()

    deliverable = months["periods"][0]["deliverables"][0]["id"]

    check(
        "reviewing work on it",
        client.post(
            f"/retainers/deliverables/{deliverable}/review",
            json={"decision": "approve"},
            headers=manager,
        ),
        404,
    )

    print("\n--- and the pulse does not twitch for it ---")

    def pulse(headers):
        r = client.get(
            "/pulse", params=[("scope", "retainers")], headers=headers
        )
        assert r.status_code == 200, r.text
        body = r.json()
        return (body["latest"], body["count"])

    before = pulse(manager)
    owner_before = pulse(owner)

    client.post(
        f"/retainers/{other}/requests",
        json={"action": "pause", "reason": "Something else."},
        headers=owner,
    )

    if pulse(manager) == before:
        ok("a change on somebody else's account is invisible to her")
    else:
        bad("the pulse ignores retainers she cannot see")

    if pulse(owner) != owner_before:
        ok("while the owner is told about it")
    else:
        bad("the owner's pulse still moves")

    print("\n--- taking her off again ---")

    check(
        "the owner removes her",
        client.delete(
            f"/retainers/{hers['id']}/assignees/{manager_id}",
            headers=owner,
        ),
        200,
    )

    gone = client.get("/retainers", headers=manager).json()

    if gone["total"] == 0:
        ok("and she stops seeing it")
    else:
        bad("removing an assignment removes the sight of it", str(gone)[:160])

    check(
        "the retainer itself closes to her too",
        client.get(f"/retainers/{hers['id']}", headers=manager),
        404,
    )

    check(
        "removing her twice says so plainly",
        client.delete(
            f"/retainers/{hers['id']}/assignees/{manager_id}",
            headers=owner,
        ),
        404,
        contains="not on this retainer",
    )

    check(
        "and she can be put back",
        client.post(
            f"/retainers/{hers['id']}/assignees",
            json={"user_id": manager_id},
            headers=owner,
        ),
        200,
    )

    if client.get("/retainers", headers=manager).json()["total"] == 1:
        ok("which gives the sight of it back")
    else:
        bad("re-assigning restores the view")

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")

    for label in FAILED:
        print("  FAILED:", label)

    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
