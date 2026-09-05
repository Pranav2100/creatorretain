from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.database.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: Session, model: type[ModelType]):
        self.db = db
        self.model = model

    def get(self, id: UUID) -> ModelType | None:
        return self.db.get(self.model, id)

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def save(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def add(self, obj: ModelType) -> ModelType:
        """
        Stages an object without committing.

        Use together with commit() when several rows must
        change atomically (for example ownership transfer).
        """
        self.db.add(obj)
        return obj

    def commit(self) -> None:
        self.db.commit()

    def delete(self, obj: ModelType) -> None:
        self.db.delete(obj)
        self.db.commit()
