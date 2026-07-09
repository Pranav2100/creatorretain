from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user import User
from app.database.repositories.base import BaseRepository
from uuid import UUID


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None
    
    def get_by_id(
        self,
        user_id: UUID,
    ):
        return (
            self.db.query(self.model)
            .filter(
                self.model.id == user_id,
            )
            .first()
        )