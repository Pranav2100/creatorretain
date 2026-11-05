"""
Roles a workspace invents, and the one rule that has to hold.

The feature is small - a name and a set of permissions - and the
interesting part is entirely about what it must refuse. One
sentence is being defended here:

    nobody ends up holding a permission they could not already
    have granted by hand.

A permission system is not proved by watching it allow things. It
is proved by trying every way round it anybody might think of,
which is most of this file: giving yourself a role, building a
role out of permissions you have not got, laundering one through
somebody else, editing a role after it has been handed out,
deleting a role too powerful to have built, and reaching a
workspace's roles from outside it.

The other half is that a custom role genuinely works - a Manager
handed one can do the thing it grants, through the ordinary
route, not just in the roles endpoint's own answer.
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


def workspace(headers, name, slug, kind="agency"):
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


def make_role(headers, name, permissions):
    return client.post(
        "/workspace-roles",
        json={"name": name, "permissions": permissions},
        headers=headers,
    )


def give(headers, user_id, role_id):
    return client.post(
        f"/workspace-roles/members/{user_id}",
        json={"role_id": role_id},
        headers=headers,
    )


def take(headers, user_id, role_id):
    return client.delete(
        f"/workspace-roles/members/{user_id}/{role_id}",
        headers=headers,
    )


# ----------------------------------------------------------------------
# Cast
# ----------------------------------------------------------------------

owner = register("owner@rolescheck.com", "Olive")
workspace(owner, "TalentX", "talentx_roles")

admin = join(owner, "admin@rolescheck.com", "admin", "Adam")
manager = join(owner, "manager@rolescheck.com", "manager", "Mira")
member = join(owner, "member@rolescheck.com", "member", "Mo")
second_manager = join(
    owner, "manager2@rolescheck.com", "manager", "Nina"
)

outsider = register("outsider@rolescheck.com", "Oscar")
workspace(outsider, "Rival", "rival_roles")

print()
print("=" * 62)
print("A workspace with no roles yet")
print("=" * 62)

listing = client.get("/workspace-roles", headers=owner)
check("the owner can read the (empty) role list", listing, 200)

if listing.status_code == 200:
    body = listing.json()

    if body["roles"] == []:
        ok("a new workspace starts with no roles of its own")
    else:
        bad("a new workspace already had roles", str(body["roles"]))

    # The vocabulary comes from the server, so the web app cannot
    # drift out of step with it.
    if len(body["permissions"]) >= 14:
        ok(f"the list ships all {len(body['permissions'])} permissions")
    else:
        bad(
            "the permission vocabulary is short",
            str(len(body["permissions"])),
        )

    held = {p["value"] for p in body["permissions"] if p["held"]}

    if "delete_workspace" in held:
        ok("it marks which ones the owner holds")
    else:
        bad("the owner is not shown as holding delete_workspace")

mgr_list = client.get("/workspace-roles", headers=manager)

if mgr_list.status_code == 200:
    mgr_held = {
        p["value"] for p in mgr_list.json()["permissions"] if p["held"]
    }

    if "delete_workspace" not in mgr_held and (
        "manage_retainers" in mgr_held
    ):
        ok("a manager is shown holding only what a manager holds")
    else:
        bad("the manager's held set is wrong", str(sorted(mgr_held)))
else:
    bad("a manager cannot read the role list", mgr_list.text)

print()
print("=" * 62)
print("Who may define a role at all")
print("=" * 62)

check(
    "a member cannot invent a role",
    make_role(member, "Member Made", ["view_retainers"]),
    403,
)

check(
    "a manager cannot invent a role",
    make_role(manager, "Manager Made", ["view_retainers"]),
    403,
)

created = check(
    "an admin can invent a role",
    make_role(
        admin,
        "Account Lead",
        ["view_retainers", "manage_retainers", "assign_retainers"],
    ),
    201,
)

lead_id = created.json()["id"] if created.status_code == 201 else None

check(
    "the owner can invent one too",
    make_role(owner, "Biller", ["manage_billing"]),
    201,
)

check(
    "two roles cannot share a name",
    make_role(owner, "Account Lead", ["view_retainers"]),
    409,
    "already a role",
)

check(
    "nor the same name in another case",
    make_role(owner, "account lead", ["view_retainers"]),
    409,
)

check(
    "a role has to grant something",
    make_role(owner, "Empty", []),
    422,
)

check(
    "an invented permission is refused",
    make_role(owner, "Sneaky", ["delete_everything"]),
    409,
    "not a permission",
)

check(
    "a nameless role is refused",
    make_role(owner, "   ", ["view_retainers"]),
    409,
    "name",
)

print()
print("=" * 62)
print("You cannot put into a role what you have not got")
print("=" * 62)

# The admin has no DELETE_WORKSPACE and no TRANSFER_OWNERSHIP.
check(
    "an admin cannot build a role that deletes the workspace",
    make_role(admin, "Nuke", ["delete_workspace"]),
    403,
    "do not have",
)

check(
    "an admin cannot sneak it in beside things they do hold",
    make_role(
        admin,
        "Mostly Fine",
        ["view_retainers", "transfer_ownership"],
    ),
    403,
)

check(
    "an admin can build one from what they do hold",
    make_role(admin, "Inviter", ["invite_members", "view_members"]),
    201,
)

print()
print("=" * 62)
print("You cannot give a role to yourself, or to a peer")
print("=" * 62)

admin_id = me(admin)
manager_id = me(manager)
member_id = me(member)
second_manager_id = me(second_manager)
owner_id = me(owner)

if lead_id:
    check(
        "an admin cannot give themselves a role",
        give(admin, admin_id, lead_id),
        403,
    )

    check(
        "an admin can give it to a manager",
        give(admin, manager_id, lead_id),
        204,
    )

    check(
        "and to a member",
        give(admin, member_id, lead_id),
        204,
    )

    check(
        "nobody can give a role to the owner",
        give(admin, owner_id, lead_id),
        403,
    )

    check(
        "the owner cannot give one to themselves either",
        give(owner, owner_id, lead_id),
        403,
    )

print()
print("=" * 62)
print("A granted role actually works, by the ordinary route")
print("=" * 62)

# Account Lead carries ASSIGN_RETAINERS, which a Manager does not
# normally have. The roles endpoint saying so proves nothing; the
# real test is whether the rest of the application now agrees.
if lead_id:
    after = client.get("/workspace-roles", headers=manager)

    if after.status_code == 200:
        held = {
            p["value"] for p in after.json()["permissions"] if p["held"]
        }

        if "assign_retainers" in held:
            ok("the manager now holds assign_retainers")
        else:
            bad(
                "the granted permission did not reach the context",
                str(sorted(held)),
            )

        if "delete_workspace" not in held:
            ok("and still does not hold what the role never gave")
        else:
            bad("the manager somehow gained delete_workspace")

    # Defining roles needs CHANGE_ROLES, which Account Lead does
    # not carry - so this must still be refused.
    check(
        "a role that does not grant CHANGE_ROLES does not unlock it",
        make_role(manager, "Still No", ["view_retainers"]),
        403,
    )

print()
print("=" * 62)
print("Laundering a permission through somebody else")
print("=" * 62)

# The owner gives the manager the power to manage roles. From
# there the manager may delegate, but only down to what they
# themselves hold - which is the whole point.
delegator = make_role(
    owner,
    "Role Keeper",
    ["change_roles", "view_members"],
)

keeper_id = (
    delegator.json()["id"] if delegator.status_code == 201 else None
)

if keeper_id:
    check(
        "the owner can hand a manager the power to manage roles",
        give(owner, manager_id, keeper_id),
        204,
    )

    check(
        "that manager can now invent a role",
        make_role(manager, "Mira's Role", ["view_retainers"]),
        201,
    )

    check(
        "but still cannot build one beyond their own ceiling",
        make_role(manager, "Mira's Power Grab", ["manage_billing"]),
        403,
        "do not have",
    )

    check(
        "and cannot hand out a role built by somebody senior",
        # Biller grants MANAGE_BILLING, which the manager has not
        # got. Somebody else having built it changes nothing.
        give(
            manager,
            member_id,
            next(
                r["id"]
                for r in client.get(
                    "/workspace-roles", headers=owner
                ).json()["roles"]
                if r["name"] == "Biller"
            ),
        ),
        403,
    )

    check(
        "nor give a role to another manager, who is their equal",
        give(manager, second_manager_id, keeper_id),
        403,
    )

    check(
        "but may give one to a member, who is below them",
        give(manager, member_id, keeper_id),
        204,
    )

print()
print("=" * 62)
print("Editing and deleting are gated the same way")
print("=" * 62)

biller_id = next(
    r["id"]
    for r in client.get("/workspace-roles", headers=owner).json()[
        "roles"
    ]
    if r["name"] == "Biller"
)

check(
    "an admin cannot edit a role granting what they have not got",
    client.patch(
        f"/workspace-roles/{biller_id}",
        json={"name": "Renamed Biller"},
        headers=admin,
    ),
    403,
)

check(
    "nor quietly strip it down to something harmless",
    client.patch(
        f"/workspace-roles/{biller_id}",
        json={"permissions": ["view_retainers"]},
        headers=admin,
    ),
    403,
)

check(
    "nor delete it",
    client.delete(f"/workspace-roles/{biller_id}", headers=admin),
    403,
)

check(
    "the owner can edit it",
    client.patch(
        f"/workspace-roles/{biller_id}",
        json={"name": "Billing"},
        headers=owner,
    ),
    200,
)

if lead_id:
    check(
        "an admin can edit a role within their reach",
        client.patch(
            f"/workspace-roles/{lead_id}",
            json={"permissions": ["view_retainers", "manage_retainers"]},
            headers=admin,
        ),
        200,
    )

    # Editing a role changes what its holders can do, immediately.
    regrant = client.get("/workspace-roles", headers=manager)

    if regrant.status_code == 200:
        held = {
            p["value"]
            for p in regrant.json()["permissions"]
            if p["held"]
        }

        if "assign_retainers" not in held:
            ok("editing a role takes the permission off its holders")
        else:
            bad("the manager kept a permission the role no longer has")

print()
print("=" * 62)
print("Taking a role back")
print("=" * 62)

if lead_id:
    check(
        "a member cannot take a role off anybody",
        take(member, manager_id, lead_id),
        403,
    )

    check(
        "an admin can take it back",
        take(admin, manager_id, lead_id),
        204,
    )

    check(
        "taking it twice says they have not got it",
        take(admin, manager_id, lead_id),
        404,
    )

    check(
        "and it can be given again",
        give(admin, manager_id, lead_id),
        204,
    )

print()
print("=" * 62)
print("Another workspace's roles are not found, not forbidden")
print("=" * 62)

if lead_id:
    check(
        "there is no single-role read endpoint to probe",
        client.get(f"/workspace-roles/{lead_id}", headers=outsider),
        405,
    )

    check(
        "an outsider's own list is their own, and empty",
        client.get("/workspace-roles", headers=outsider),
        200,
        '"roles":[]',
    )

    check(
        "an outsider cannot edit one",
        client.patch(
            f"/workspace-roles/{lead_id}",
            json={"name": "Mine Now"},
            headers=outsider,
        ),
        404,
    )

    check(
        "an outsider cannot delete one",
        client.delete(
            f"/workspace-roles/{lead_id}", headers=outsider
        ),
        404,
    )

    check(
        "an outsider cannot hand it to themselves",
        give(outsider, me(outsider), lead_id),
        404,
    )

    check(
        "signed out, nothing at all",
        client.get("/workspace-roles"),
        401,
    )

print()
print("=" * 62)
print("Ordering is presentation, not authority")
print("=" * 62)

roles_now = client.get("/workspace-roles", headers=owner).json()[
    "roles"
]
ids = [r["id"] for r in roles_now]

check(
    "the owner can reorder the list",
    client.put(
        "/workspace-roles/order",
        json={"role_ids": list(reversed(ids))},
        headers=owner,
    ),
    200,
)

check(
    "a partial list is refused",
    client.put(
        "/workspace-roles/order",
        json={"role_ids": ids[:1]},
        headers=owner,
    ),
    409,
    "whole list",
)

check(
    "a duplicate in the order is refused",
    client.put(
        "/workspace-roles/order",
        json={"role_ids": [ids[0]] * len(ids)},
        headers=owner,
    ),
    409,
)

check(
    "somebody with no role of their own cannot reorder",
    client.put(
        "/workspace-roles/order",
        json={"role_ids": list(reversed(ids))},
        headers=second_manager,
    ),
    403,
)

# The member was handed Role Keeper earlier, which carries
# CHANGE_ROLES - so they genuinely can. Worth asserting rather
# than assuming: it is the delegation chain working end to end,
# two people removed from the owner who set it up.
check(
    "but the member handed Role Keeper can, because it grants it",
    client.put(
        "/workspace-roles/order",
        json={"role_ids": list(reversed(ids))},
        headers=member,
    ),
    200,
)

# Moving a role to the top must not change what it can do. The
# manager holds Role Keeper; reordering should leave that exactly
# as it was.
if keeper_id:
    after_order = client.get("/workspace-roles", headers=manager)

    if after_order.status_code == 200:
        held = {
            p["value"]
            for p in after_order.json()["permissions"]
            if p["held"]
        }

        if "manage_billing" not in held:
            ok("reordering granted nobody anything")
        else:
            bad("reordering changed what somebody can do")

print()
print("=" * 62)
print("Deleting a role takes it off everyone")
print("=" * 62)

if keeper_id:
    check(
        "the owner deletes Role Keeper",
        client.delete(
            f"/workspace-roles/{keeper_id}", headers=owner
        ),
        204,
    )

    gone = client.get("/workspace-roles", headers=manager)

    if gone.status_code == 200:
        held = {
            p["value"] for p in gone.json()["permissions"] if p["held"]
        }

        if "change_roles" not in held:
            ok("the manager lost the power it carried")
        else:
            bad("deleting the role left its permissions behind")

    check(
        "and the manager can no longer invent roles",
        make_role(manager, "Too Late", ["view_retainers"]),
        403,
    )

    check(
        "deleting it twice is not found",
        client.delete(
            f"/workspace-roles/{keeper_id}", headers=owner
        ),
        404,
    )

print()
print("=" * 62)
print("Who holds what, for the Team list")
print("=" * 62)

assigned = client.get("/workspace-roles/assignments", headers=owner)
check("the owner can read the assignments", assigned, 200)

if assigned.status_code == 200:
    held = assigned.json()["assignments"]

    # Account Lead was given back to the manager further up.
    if lead_id and lead_id in held.get(manager_id, []):
        ok("it reports the manager holding Account Lead")
    else:
        bad("the manager's grant is missing", str(held))

    # Role Keeper was deleted, so nothing should still mention it.
    if keeper_id and not any(
        keeper_id in roles for roles in held.values()
    ):
        ok("and nothing still points at the deleted role")
    else:
        bad("a deleted role is still assigned to somebody", str(held))

check(
    "an outsider sees only their own workspace",
    client.get("/workspace-roles/assignments", headers=outsider),
    200,
    '"assignments":{}',
)

check(
    "signed out, nothing",
    client.get("/workspace-roles/assignments"),
    401,
)

print()
print(f"{len(PASSED)} passed, {len(FAILED)} failed")

if FAILED:
    print()
    for label in FAILED:
        print("  FAILED: " + label)
