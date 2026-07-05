from enum import Enum


class WorkspaceMemberStatus(str, Enum):
    ACTIVE = "active"
    REMOVED = "removed"