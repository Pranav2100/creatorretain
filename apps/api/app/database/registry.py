"""
Imports every SQLAlchemy model.

Alembic imports this file so Base.metadata
contains every table in the application.
"""

from app.database.models.base import Base
from app.database.models.user import User

__all__ = [
    "Base",
    "User",
]