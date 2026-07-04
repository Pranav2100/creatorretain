from enum import Enum


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    DELETED = "deleted"