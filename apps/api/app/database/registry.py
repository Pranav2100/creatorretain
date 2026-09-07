"""
Import every SQLAlchemy model here.

Alembic imports this file so metadata contains
every table in the application.
"""

from app.database.models.base import Base

# Import every model here
from app.database.models.content_category import ContentCategory
from app.database.models.creator_portfolio_item import (
    CreatorPortfolioItem,
)
from app.database.models.creator_profile import CreatorProfile
from app.database.models.creator_rate import CreatorRate
from app.database.models.creator_social_account import (
    CreatorSocialAccount,
)
from app.database.models.user import User
from app.database.models.workspace import Workspace
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.database.models.workspace_member import WorkspaceMember

__all__ = [
    "Base",
    "User",
    "ContentCategory",
    "CreatorProfile",
    "CreatorSocialAccount",
    "CreatorPortfolioItem",
    "CreatorRate",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvitation",
]