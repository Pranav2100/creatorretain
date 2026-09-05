"""
Import every SQLAlchemy model here.

Alembic imports this file so metadata contains
every table in the application.
"""

from app.database.models.base import Base

# Import every model here
from app.database.models.user import User
from app.database.models.workspace import Workspace
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.database.models.workspace_member import WorkspaceMember

__all__ = [
    "Base",
    "User",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvitation",
]