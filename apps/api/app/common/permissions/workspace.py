from enum import StrEnum

from app.common.enums import WorkspaceRole


class WorkspacePermission(StrEnum):
    # The name, bio and logo are what a creator reads before
    # accepting an offer, so rewriting them is not a Member's to do.
    EDIT_WORKSPACE = "edit_workspace"

    VIEW_MEMBERS = "view_members"
    INVITE_MEMBERS = "invite_members"
    MANAGE_INVITATIONS = "manage_invitations"
    REMOVE_MEMBERS = "remove_members"
    CHANGE_ROLES = "change_roles"
    TRANSFER_OWNERSHIP = "transfer_ownership"
    MANAGE_BILLING = "manage_billing"
    DELETE_WORKSPACE = "delete_workspace"
    LEAVE_WORKSPACE = "leave_workspace"

    # Signing a retainer commits the workspace to paying money
    # every month. Reading one does not, and a Member kept in the
    # loop needs to know what was agreed and what is due.
    VIEW_RETAINERS = "view_retainers"
    MANAGE_RETAINERS = "manage_retainers"

    # Deciding who runs which account. Separate from managing the
    # retainer itself, because the person who runs an account and
    # the person who decides who runs it are different jobs.
    ASSIGN_RETAINERS = "assign_retainers"

    # Whether this role sees the whole workspace's retainers or
    # only the ones put in their hands. Held by the seniors rather
    # than checked as an absence, so a new role added later is
    # narrow until someone decides otherwise.
    VIEW_ALL_RETAINERS = "view_all_retainers"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[WorkspacePermission]] = {
    WorkspaceRole.OWNER: frozenset(
        {
            WorkspacePermission.EDIT_WORKSPACE,
            WorkspacePermission.VIEW_MEMBERS,
            WorkspacePermission.INVITE_MEMBERS,
            WorkspacePermission.MANAGE_INVITATIONS,
            WorkspacePermission.REMOVE_MEMBERS,
            WorkspacePermission.CHANGE_ROLES,
            WorkspacePermission.TRANSFER_OWNERSHIP,
            WorkspacePermission.MANAGE_BILLING,
            WorkspacePermission.DELETE_WORKSPACE,
            WorkspacePermission.VIEW_RETAINERS,
            WorkspacePermission.VIEW_ALL_RETAINERS,
            WorkspacePermission.MANAGE_RETAINERS,
            WorkspacePermission.ASSIGN_RETAINERS,
        }
    ),
    WorkspaceRole.ADMIN: frozenset(
        {
            WorkspacePermission.EDIT_WORKSPACE,
            WorkspacePermission.VIEW_MEMBERS,
            WorkspacePermission.INVITE_MEMBERS,
            WorkspacePermission.MANAGE_INVITATIONS,
            WorkspacePermission.REMOVE_MEMBERS,
            WorkspacePermission.CHANGE_ROLES,
            WorkspacePermission.LEAVE_WORKSPACE,
            WorkspacePermission.VIEW_RETAINERS,
            WorkspacePermission.VIEW_ALL_RETAINERS,
            WorkspacePermission.MANAGE_RETAINERS,
            WorkspacePermission.ASSIGN_RETAINERS,
        }
    ),
    # The person who runs accounts. Everything a retainer needs -
    # offering, pausing, reviewing the work - and nothing about
    # the company: no inviting, no removing, no rewriting the page
    # creators read. Sees only the retainers put in their hands,
    # which is the whole point of the role: an agency with forty
    # creators does not want each manager wading through all of
    # them to find their three.
    WorkspaceRole.MANAGER: frozenset(
        {
            WorkspacePermission.LEAVE_WORKSPACE,
            WorkspacePermission.VIEW_MEMBERS,
            WorkspacePermission.VIEW_RETAINERS,
            WorkspacePermission.MANAGE_RETAINERS,
        }
    ),
    WorkspaceRole.MEMBER: frozenset(
        {
            WorkspacePermission.LEAVE_WORKSPACE,
            WorkspacePermission.VIEW_RETAINERS,
            WorkspacePermission.VIEW_ALL_RETAINERS,
        }
    ),
}


def permissions_for(
    role: WorkspaceRole,
) -> frozenset[WorkspacePermission]:
    """
    What the built-in role alone grants.

    The floor, not the whole story: a person may also hold custom
    roles, which only ever add to this. Ask the WorkspaceContext
    rather than this function if you want what somebody can
    actually do.
    """
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(
    role: WorkspaceRole,
    permission: WorkspacePermission,
) -> bool:
    return permission in permissions_for(role)


# ----------------------------------------------------------------------
# Custom roles
#
# A workspace can invent roles of its own. Everything below exists
# to make one rule true no matter how they are combined:
#
#     nobody ends up holding a permission they could not already
#     grant by hand.
#
# Which is enforced by subset, not by ordering. Discord sorts
# roles by height and asks whether yours sits above theirs; here
# a role carries no authority of its own, and the question is
# always the plainer one - is everything in this role something
# you already hold? That needs no explaining to the person using
# it, and it cannot be gamed by dragging a row up a list.
# ----------------------------------------------------------------------


def can_define_roles(held: frozenset[WorkspacePermission]) -> bool:
    """
    Whether this person may invent roles at all.

    Reuses CHANGE_ROLES rather than adding a permission of its
    own. Defining a role and handing one out are the same job -
    deciding what other people can do - and a separate permission
    would start life held by nobody, since there would be no role
    to put it in.
    """
    return WorkspacePermission.CHANGE_ROLES in held


def can_shape_role(
    held: frozenset[WorkspacePermission],
    wanted: frozenset[WorkspacePermission],
    existing: frozenset[WorkspacePermission] = frozenset(),
) -> bool:
    """
    Whether this person may create a role granting `wanted`, or
    change one that currently grants `existing` into one granting
    `wanted`.

    Both sets have to be within reach, and the second half is the
    one that is easy to miss. Checking only `wanted` would let
    somebody who cannot grant MANAGE_BILLING take a role that
    grants it and quietly edit it down to something harmless -
    stripping a permission from everyone holding that role, which
    is a change they had no business making. So editing a role
    requires holding what it already gives out, as well as what
    it would give out next.
    """
    return wanted <= held and existing <= held


def can_grant_role(
    actor_role: WorkspaceRole,
    held: frozenset[WorkspacePermission],
    target_role: WorkspaceRole,
    role_grants: frozenset[WorkspacePermission],
) -> bool:
    """
    Whether this person may put this role on that person.

    Three things, and each one closes a different door.

    Outranking the target is what stops self-promotion: you never
    outrank yourself, so there is no arrangement of roles that
    lets somebody hand themselves anything. It also stops peers
    editing each other, the same way removing a member does.

    Holding everything the role grants is what stops laundering a
    permission through a role somebody else built - a Manager who
    can grant roles still cannot hand out MANAGE_BILLING, because
    they have not got it to give.

    And the Owner is left out entirely. They already hold
    everything a custom role could add, so granting one to them
    could only ever be noise.
    """
    if target_role == WorkspaceRole.OWNER:
        return False

    if not actor_role.outranks(target_role):
        return False

    return role_grants <= held


def can_remove_member(
    actor_role: WorkspaceRole,
    target_role: WorkspaceRole,
) -> bool:
    """
    You can remove people below you, and nobody else.

    Which keeps the two rules that matter however many roles
    there turn out to be: an Admin cannot remove another Admin,
    and nobody removes the Owner. An Owner leaves by handing the
    workspace on, not by being voted out of it.
    """
    if target_role == WorkspaceRole.OWNER:
        return False

    return actor_role.outranks(target_role)


def can_change_role(
    actor_role: WorkspaceRole,
    target_role: WorkspaceRole,
    new_role: WorkspaceRole,
) -> bool:
    """
    You can change people below you, to anything up to your own
    level.

    Up to and including: an Admin promoting someone to Admin is
    ordinary delegation, and refusing it would leave only the
    Owner able to grow the team. What an Admin cannot do is touch
    another Admin, in either direction - and that falls out of
    the first half of the rule rather than needing its own.

    Ownership is not a role anyone is promoted into. It moves by
    transfer, which is a different operation with its own
    confirmation.
    """
    if WorkspaceRole.OWNER in (target_role, new_role):
        return False

    return actor_role.outranks(target_role) and (
        actor_role.rank >= new_role.rank
    )
