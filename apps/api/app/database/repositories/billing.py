from uuid import UUID

from sqlalchemy import case
from sqlalchemy.orm import Session

from app.common.enums.subscription import SubscriptionStatus
from app.database.models.subscription import (
    BillingEvent,
    Subscription,
)
from app.database.repositories.base import BaseRepository


class BillingRepository(BaseRepository[Subscription]):
    def __init__(self, db: Session):
        super().__init__(db, Subscription)

    def live_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Subscription | None:
        """
        The subscription a workspace currently has, if any.

        Ordered explicitly rather than by the status column: an
        enum sorts by its declaration order on PostgreSQL and
        alphabetically on the VARCHAR fallback, so ordering by it
        gives different answers on different databases.
        """
        ranked = case(
            (Subscription.status == SubscriptionStatus.ACTIVE, 0),
            (Subscription.status == SubscriptionStatus.PAST_DUE, 1),
            (
                Subscription.status == SubscriptionStatus.CANCELLING,
                2,
            ),
            (Subscription.status == SubscriptionStatus.PENDING, 3),
            else_=4,
        )

        return (
            self.db.query(Subscription)
            .filter(
                Subscription.workspace_id == workspace_id,
                Subscription.deleted_at.is_(None),
                Subscription.status != SubscriptionStatus.ENDED,
            )
            .order_by(ranked.asc(), Subscription.created_at.desc())
            .first()
        )

    def pending_for_workspace(
        self,
        workspace_id: UUID,
    ) -> list[Subscription]:
        """
        Every unpaid checkout a workspace is holding.

        Normally at most one, because starting a new one
        supersedes the last. This exists so a cancel can also
        clear up rows left behind before that was true.
        """
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.workspace_id == workspace_id,
                Subscription.deleted_at.is_(None),
                Subscription.status == SubscriptionStatus.PENDING,
            )
            .all()
        )

    def by_provider_ref(
        self,
        provider: str,
        provider_subscription_id: str,
    ) -> Subscription | None:
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.provider == provider,
                Subscription.provider_subscription_id
                == provider_subscription_id,
            )
            .first()
        )

    def create(
        self,
        workspace_id: UUID,
        provider: str,
        provider_subscription_id: str,
        plan,
        amount: int | None,
    ) -> Subscription:
        row = Subscription(
            workspace_id=workspace_id,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            plan=plan,
            status=SubscriptionStatus.PENDING,
            amount=amount,
        )

        self.db.add(row)
        self.db.flush()

        return row

    # ------------------------------------------------------------------
    # Webhook bookkeeping
    # ------------------------------------------------------------------

    def already_handled(
        self,
        provider: str,
        event_id: str,
    ) -> bool:
        return (
            self.db.query(BillingEvent)
            .filter(
                BillingEvent.provider == provider,
                BillingEvent.event_id == event_id,
            )
            .first()
            is not None
        )

    def record_event(
        self,
        provider: str,
        event_id: str,
        kind: str,
        provider_subscription_id: str | None,
    ) -> BillingEvent:
        row = BillingEvent(
            provider=provider,
            event_id=event_id,
            kind=kind,
            provider_subscription_id=provider_subscription_id,
        )

        self.db.add(row)
        self.db.flush()

        return row

    def history(
        self,
        workspace_id: UUID,
        limit: int = 20,
    ) -> list[Subscription]:
        return (
            self.db.query(Subscription)
            .filter(Subscription.workspace_id == workspace_id)
            .order_by(Subscription.created_at.desc())
            .limit(limit)
            .all()
        )
