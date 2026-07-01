"""
Import every SQLAlchemy model here.

Alembic imports this file so metadata contains
every table in the application.
"""

from app.database.models.base import Base

# Import models below
# from app.database.models.user import User

__all__ = ["Base"]