from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.common.enums import RetainerStatus
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
from app.database.models.retainer_period import RetainerPeriod

# How many recent reviews the median is taken over. Recency matters
# more than a lifetime average: an agency that answered quickly a
# year ago and sits on work now should read as slow.
REVIEW_WINDOW = 20


class BrandRepository:
    """
    Reads about a hiring workspace that only the platform can make:
    counted from the retainer tables, never from anything the
    workspace itself wrote down.
    """

    def __init__(self, db: Session):
        self.db = db

    def count_live_retainers(self, workspace_id: UUID) -> int:
        """
        A retainer under notice is still live - the work and the
        money both continue until the date runs out. One past that
        date is not, even though nothing rewrote its status.
        """
        today = date.today()

        return (
            self.db.execute(
                select(func.count())
                .select_from(Retainer)
                .where(
                    Retainer.brand_workspace_id == workspace_id,
                    Retainer.status == RetainerStatus.ACTIVE,
                    Retainer.deleted_at.is_(None),
                    or_(
                        Retainer.end_date.is_(None),
                        Retainer.end_date >= today,
                    ),
                )
            ).scalar_one()
            or 0
        )

    def count_creators_worked_with(self, workspace_id: UUID) -> int:
        """
        Distinct creators who actually said yes at some point.

        Pending and declined offers are left out on purpose - anyone
        can send fifty offers, and a count of those would reward
        exactly the behaviour a creator is trying to screen out.
        """
        return (
            self.db.execute(
                select(
                    func.count(
                        func.distinct(Retainer.creator_workspace_id),
                    )
                ).where(
                    Retainer.brand_workspace_id == workspace_id,
                    Retainer.status.in_(
                        (
                            RetainerStatus.ACTIVE,
                            RetainerStatus.PAUSED,
                            RetainerStatus.ENDED,
                        )
                    ),
                    Retainer.deleted_at.is_(None),
                )
            ).scalar_one()
            or 0
        )

    def recent_review_gaps(
        self,
        workspace_id: UUID,
    ) -> list[tuple[datetime, datetime]]:
        """
        The last few (submitted_at, reviewed_at) pairs for this
        workspace, newest first.

        Both columns are non-null together only while a review
        stands: resubmitting clears reviewed_at, so a row can never
        report a review that happened before the work arrived. The
        arithmetic is left to the caller, in Python, because median
        over a window is not worth a database-specific query.
        """
        rows = self.db.execute(
            select(
                RetainerDeliverable.submitted_at,
                RetainerDeliverable.reviewed_at,
            )
            .join(
                RetainerPeriod,
                RetainerPeriod.id == RetainerDeliverable.period_id,
            )
            .join(
                Retainer,
                Retainer.id == RetainerPeriod.retainer_id,
            )
            .where(
                Retainer.brand_workspace_id == workspace_id,
                Retainer.deleted_at.is_(None),
                RetainerDeliverable.submitted_at.is_not(None),
                RetainerDeliverable.reviewed_at.is_not(None),
            )
            .order_by(RetainerDeliverable.reviewed_at.desc())
            .limit(REVIEW_WINDOW)
        ).all()

        return [(row[0], row[1]) for row in rows]
