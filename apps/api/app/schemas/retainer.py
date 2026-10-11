from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import (
    DeliverableStatus,
    DeliverableType,
    RetainerStatus,
)
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
from app.database.models.retainer_period import RetainerPeriod


# ----------------------------------------------------------------------
# Requests
# ----------------------------------------------------------------------


class DeliverableSpecRequest(BaseModel):
    deliverable_type: DeliverableType
    quantity: int = Field(default=1, ge=1, le=60)
    notes: str | None = Field(default=None, max_length=300)


class CreateRetainerRequest(BaseModel):
    creator_workspace_id: UUID
    title: str = Field(min_length=2, max_length=120)
    monthly_amount: Decimal = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    deliverables: list[DeliverableSpecRequest] = Field(min_length=1)

    # Defaults to today. A future date sets the retainer up in
    # advance; it produces no periods until that day arrives.
    start_date: date | None = None
    end_date: date | None = None

    notice_period_days: int = Field(default=30, ge=0, le=180)
    terms: str | None = None
    message: str | None = None


class DeclineRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class EndRetainerRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class PauseRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class SubmitDeliverableRequest(BaseModel):
    url: str = Field(min_length=3, max_length=500)
    note: str | None = None


class ReviewDeliverableRequest(BaseModel):
    decision: DeliverableStatus
    note: str | None = Field(default=None, max_length=1000)


# ----------------------------------------------------------------------
# Responses
# ----------------------------------------------------------------------


class DeliverableSpecResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deliverable_type: DeliverableType
    quantity: int
    notes: str | None


class DeliverableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deliverable_type: DeliverableType
    position: int
    status: DeliverableStatus
    title: str | None
    submitted_url: str | None
    submitted_note: str | None
    submitted_at: datetime | None
    submission_count: int
    reviewed_at: datetime | None
    review_note: str | None


class PeriodResponse(BaseModel):
    id: UUID
    sequence: int
    period_start: date
    period_end: date
    amount: Decimal
    currency: str
    state: str
    is_complete: bool
    outstanding_count: int
    deliverables: list[DeliverableResponse]

    @classmethod
    def from_period(
        cls,
        period: RetainerPeriod,
        today: date,
    ) -> "PeriodResponse":
        return cls(
            id=period.id,
            sequence=period.sequence,
            period_start=period.period_start,
            period_end=period.period_end,
            amount=period.amount,
            currency=period.currency,
            state=period.state(today),
            is_complete=period.is_complete,
            outstanding_count=period.outstanding_count,
            deliverables=[
                DeliverableResponse.model_validate(item)
                for item in period.deliverables
            ],
        )


class RetainerParty(BaseModel):
    workspace_id: UUID
    slug: str
    display_name: str


class RetainerSummary(BaseModel):
    """What a list row shows. No periods: a list of ten retainers
    should not drag every month of every one of them along."""

    id: UUID
    title: str
    status: RetainerStatus
    monthly_amount: Decimal
    currency: str
    start_date: date
    end_date: date | None
    brand: RetainerParty
    creator: RetainerParty
    your_side: str
    monthly_deliverable_count: int
    periods_so_far: int
    created_at: datetime

    @classmethod
    def from_retainer(
        cls,
        retainer: Retainer,
        viewer_workspace_id: UUID,
    ) -> "RetainerSummary":
        return cls(
            id=retainer.id,
            title=retainer.title,
            status=retainer.status,
            monthly_amount=retainer.monthly_amount,
            currency=retainer.currency,
            start_date=retainer.start_date,
            end_date=retainer.end_date,
            brand=_party(retainer.brand_workspace),
            creator=_party(retainer.creator_workspace),
            your_side=(
                "brand"
                if viewer_workspace_id == retainer.brand_workspace_id
                else "creator"
            ),
            monthly_deliverable_count=(
                retainer.monthly_deliverable_count
            ),
            periods_so_far=len(retainer.periods),
            created_at=retainer.created_at,
        )


class RetainerDetail(BaseModel):
    id: UUID
    title: str
    status: RetainerStatus
    monthly_amount: Decimal
    currency: str
    start_date: date
    end_date: date | None
    anchor_day: int
    notice_period_days: int
    terms: str | None
    message: str | None
    brand: RetainerParty
    creator: RetainerParty
    your_side: str
    specs: list[DeliverableSpecResponse]
    periods: list[PeriodResponse]
    accepted_at: datetime | None
    responded_at: datetime | None
    paused_at: datetime | None
    ended_at: datetime | None
    ended_reason: str | None
    created_at: datetime

    @classmethod
    def from_retainer(
        cls,
        retainer: Retainer,
        side: str,
        today: date,
    ) -> "RetainerDetail":
        return cls(
            id=retainer.id,
            title=retainer.title,
            status=retainer.status,
            monthly_amount=retainer.monthly_amount,
            currency=retainer.currency,
            start_date=retainer.start_date,
            end_date=retainer.end_date,
            anchor_day=retainer.anchor_day,
            notice_period_days=retainer.notice_period_days,
            terms=retainer.terms,
            message=retainer.message,
            brand=_party(retainer.brand_workspace),
            creator=_party(retainer.creator_workspace),
            your_side=side,
            specs=[
                DeliverableSpecResponse.model_validate(spec)
                for spec in retainer.specs
            ],
            periods=[
                PeriodResponse.from_period(period, today)
                for period in retainer.periods
            ],
            accepted_at=retainer.accepted_at,
            responded_at=retainer.responded_at,
            paused_at=retainer.paused_at,
            ended_at=retainer.ended_at,
            ended_reason=retainer.ended_reason,
            created_at=retainer.created_at,
        )


class RetainerListResponse(BaseModel):
    retainers: list[RetainerSummary]
    total: int


class PeriodListResponse(BaseModel):
    periods: list[PeriodResponse]
    total: int


def _party(workspace) -> RetainerParty:
    return RetainerParty(
        workspace_id=workspace.id,
        slug=workspace.slug,
        display_name=workspace.display_name,
    )


def deliverable_response(
    deliverable: RetainerDeliverable,
) -> DeliverableResponse:
    return DeliverableResponse.model_validate(deliverable)
