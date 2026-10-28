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
from app.database.models.conversation import Conversation
from app.database.models.conversation_read import ConversationRead
from app.database.models.creator_profile import CreatorProfile
from app.database.models.creator_rate import CreatorRate
from app.database.models.creator_social_account import (
    CreatorSocialAccount,
)
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
from app.database.models.retainer_deliverable_spec import (
    RetainerDeliverableSpec,
)
from app.database.models.retainer_assignment import (
    RetainerAssignment,
)
from app.database.models.retainer_event import RetainerEvent
from app.database.models.retainer_period import RetainerPeriod
from app.database.models.message import Message
from app.database.models.user import User
from app.database.models.workspace import Workspace
from app.database.models.workspace_block import WorkspaceBlock
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.database.models.workspace_member import WorkspaceMember

__all__ = [
    "Base",
    "User",
    "ContentCategory",
    "Conversation",
    "ConversationRead",
    "Message",
    "WorkspaceBlock",
    "CreatorProfile",
    "CreatorSocialAccount",
    "CreatorPortfolioItem",
    "CreatorRate",
    "Retainer",
    "RetainerDeliverable",
    "RetainerAssignment",
    "RetainerDeliverableSpec",
    "RetainerEvent",
    "RetainerPeriod",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvitation",
]