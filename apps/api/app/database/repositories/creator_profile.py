from uuid import UUID

from sqlalchemy.orm import Session, joinedload, selectinload

from app.database.models.content_category import ContentCategory
from app.database.models.creator_portfolio_item import (
    CreatorPortfolioItem,
)
from app.database.models.creator_profile import CreatorProfile
from app.database.models.creator_rate import CreatorRate
from app.database.models.creator_social_account import (
    CreatorSocialAccount,
)
from app.database.repositories.base import BaseRepository


class CreatorProfileRepository(BaseRepository[CreatorProfile]):
    def __init__(self, db: Session):
        super().__init__(db, CreatorProfile)

    def _loaded(self):
        return self.db.query(self.model).options(
            selectinload(self.model.social_accounts),
            selectinload(self.model.portfolio_items),
            selectinload(self.model.rates),
            selectinload(self.model.categories),
            joinedload(self.model.workspace),
        )

    def get_by_workspace(
        self,
        workspace_id: UUID,
    ) -> CreatorProfile | None:
        return (
            self._loaded()
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    def get_full(self, profile_id: UUID) -> CreatorProfile | None:
        return (
            self._loaded()
            .filter(self.model.id == profile_id)
            .first()
        )

    # ------------------------------------------------------------------
    # Sub-resources
    # ------------------------------------------------------------------

    def get_social_account(
        self,
        account_id: UUID,
    ) -> CreatorSocialAccount | None:
        return self.db.get(CreatorSocialAccount, account_id)

    def get_social_account_by_platform(
        self,
        profile_id: UUID,
        platform,
    ) -> CreatorSocialAccount | None:
        return (
            self.db.query(CreatorSocialAccount)
            .filter(
                CreatorSocialAccount.profile_id == profile_id,
                CreatorSocialAccount.platform == platform,
            )
            .first()
        )

    def get_portfolio_item(
        self,
        item_id: UUID,
    ) -> CreatorPortfolioItem | None:
        return self.db.get(CreatorPortfolioItem, item_id)

    def get_rate(self, rate_id: UUID) -> CreatorRate | None:
        return self.db.get(CreatorRate, rate_id)

    def next_portfolio_position(self, profile_id: UUID) -> int:
        count = (
            self.db.query(CreatorPortfolioItem)
            .filter(CreatorPortfolioItem.profile_id == profile_id)
            .count()
        )

        return count

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def list_categories(self) -> list[ContentCategory]:
        return (
            self.db.query(ContentCategory)
            .filter(ContentCategory.is_active.is_(True))
            .order_by(ContentCategory.name.asc())
            .all()
        )

    def get_categories_by_ids(
        self,
        category_ids: list[UUID],
    ) -> list[ContentCategory]:
        if not category_ids:
            return []

        return (
            self.db.query(ContentCategory)
            .filter(
                ContentCategory.id.in_(category_ids),
                ContentCategory.is_active.is_(True),
            )
            .all()
        )
