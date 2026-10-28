from enum import StrEnum


class InvitableWorkspaceRole(StrEnum):
    """
    The roles an invitation may name.

    Owner is absent on purpose: a workspace gets its owner by
    being created or by having ownership handed over, never by
    someone emailing an invitation to the job.
    """

    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
