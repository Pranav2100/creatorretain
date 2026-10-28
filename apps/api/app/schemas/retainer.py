from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.common.enums import (
    DeliverableStatus,
    DeliverableType,
    RetainerEventKind,
    RetainerRequest,
    RetainerStatus,
    ReviewDecision,
    type_rank,
)
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
from app.database.models.retainer_event import RetainerEvent
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


class ChangeRequestBody(BaseModel):
    """Asking the other side to pause or to resume."""

    action: RetainerRequest
    reason: str | None = Field(default=None, max_length=300)


class SubmitDeliverableRequest(BaseModel):
    # A real link, not any string. The brand clicks this to see the
    # work, so "done" in the url field helps nobody.
    url: AnyHttpUrl = Field(max_length=500)
    note: str | None = None


class ReviewDeliverableRequest(BaseModel):
    # Three choices, not the whole status enum. The API used to
    # advertise five and refuse two of them at runtime.
    decision: ReviewDecision
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
                for item in sorted(
                    period.deliverables,
                    key=_deliverable_order,
                )
            ],
        )


class RetainerParty(BaseModel):
    workspace_id: UUID
    slug: str
    display_name: str


class Contact(BaseModel):
    """
    The person at the hiring end, rather than the company.

    A creator weighing up an offer is deciding whether to work
    with someone, and "TalentX" is not someone. This is who sent
    it, what they do there, and how to reach them - the
    difference between a letter from a company and a letter from
    a person at one.

    Null for a retainer offered before this existed, and for one
    whose sender has since left: the agreement outlives the
    employee, so the page has to read sensibly without them.
    """

    name: str
    job_title: str | None
    email: str
    phone: str | None


class PendingChange(BaseModel):
    """
    A change one side has asked for and the other has not answered.

    `yours` saves the reader working out whose it is: the same
    request reads as "waiting on them" to one party and "waiting on
    you" to the other, and only one of them gets buttons.
    """

    action: RetainerRequest
    by_side: str
    yours: bool
    reason: str | None
    asked_at: datetime


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

    # Enough for a list row to say something is up without
    # carrying the whole request along.
    under_notice: bool
    awaiting_you: bool

    created_at: datetime

    @classmethod
    def from_retainer(
        cls,
        retainer: Retainer,
        viewer_workspace_id: UUID,
        today: date,
    ) -> "RetainerSummary":
        side = (
            "brand"
            if viewer_workspace_id == retainer.brand_workspace_id
            else "creator"
        )

        return cls(
            id=retainer.id,
            title=retainer.title,
            # Derived, so one whose notice ran out last week reads
            # as ended without anything having had to run.
            status=retainer.state(today),
            monthly_amount=retainer.monthly_amount,
            currency=retainer.currency,
            start_date=retainer.start_date,
            end_date=retainer.end_date,
            brand=_party(retainer.brand_workspace),
            creator=_party(retainer.creator_workspace),
            your_side=side,
            monthly_deliverable_count=(
                retainer.monthly_deliverable_count
            ),
            periods_so_far=len(retainer.periods),
            under_notice=retainer.is_under_notice(today),
            awaiting_you=(
                retainer.pending_action is not None
                and retainer.pending_by_side != side
            ),
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

    # Only ever the hiring side's person. The creator is the other
    # party to the agreement, not a contact to be listed.
    contact: Contact | None

    your_side: str
    specs: list[DeliverableSpecResponse]
    periods: list[PeriodResponse]
    accepted_at: datetime | None
    responded_at: datetime | None
    paused_at: datetime | None
    ended_at: datetime | None
    ended_reason: str | None

    pending: PendingChange | None
    under_notice: bool
    notice_given_at: datetime | None
    notice_given_by_side: str | None

    created_at: datetime

    @classmethod
    def from_retainer(
        cls,
        retainer: Retainer,
        side: str,
        today: date,
    ) -> "RetainerDetail":
        pending = None

        if retainer.pending_action is not None:
            pending = PendingChange(
                action=retainer.pending_action,
                by_side=retainer.pending_by_side or "",
                yours=retainer.pending_by_side == side,
                reason=retainer.pending_reason,
                asked_at=retainer.pending_at,
            )

        return cls(
            id=retainer.id,
            title=retainer.title,
            status=retainer.state(today),
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
            contact=_contact(retainer.created_by),
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
            pending=pending,
            under_notice=retainer.is_under_notice(today),
            notice_given_at=retainer.notice_given_at,
            notice_given_by_side=retainer.notice_given_by_side,
            created_at=retainer.created_at,
        )


class EventResponse(BaseModel):
    """
    One line of history, as facts rather than as a sentence.

    The wording is left to the reader's side, because the same
    event reads differently depending on who is looking at it -
    "you asked to pause this" against "Nina Cooks asked to pause
    this" - and a sentence baked in here would have to be one or
    the other.
    """

    id: UUID
    kind: RetainerEventKind
    at: datetime

    # The workspace, as it read on the day.
    actor_name: str | None

    # The human being, looked up live rather than copied.
    #
    # The workspace name is frozen at the time because renaming a
    # company should not rewrite what it did; a person's name is
    # not, because someone who corrects their own surname means it
    # retrospectively. Null once they have left and the row's
    # reference to them has been cleared.
    actor_person: str | None

    actor_side: str | None
    yours: bool
    note: str | None
    subject: str | None
    about_work: bool

    @classmethod
    def from_event(
        cls,
        event: RetainerEvent,
        side: str,
    ) -> "EventResponse":
        return cls(
            id=event.id,
            kind=event.kind,
            at=event.created_at,
            actor_name=event.actor_name,
            actor_person=(
                f"{event.actor.first_name} {event.actor.last_name}".strip()
                if event.actor is not None
                else None
            ),
            actor_side=event.actor_side,
            yours=event.actor_side == side,
            note=event.note,
            subject=event.subject,
            about_work=event.kind.is_about_work,
        )


class AssignRequest(BaseModel):
    user_id: UUID


class Assignee(BaseModel):
    """Someone inside the hiring workspace who runs this account."""

    user_id: UUID
    name: str
    job_title: str | None
    email: str
    assigned_at: datetime

    @classmethod
    def from_assignment(cls, assignment) -> "Assignee":
        user = assignment.user

        return cls(
            user_id=user.id,
            name=f"{user.first_name} {user.last_name}".strip(),
            job_title=user.job_title,
            email=user.email,
            assigned_at=assignment.created_at,
        )


class AssigneeListResponse(BaseModel):
    assignees: list[Assignee]
    total: int


class EventListResponse(BaseModel):
    events: list[EventResponse]
    total: int


class RetainerListResponse(BaseModel):
    retainers: list[RetainerSummary]
    total: int


class PeriodListResponse(BaseModel):
    periods: list[PeriodResponse]
    total: int


def _deliverable_order(item) -> tuple[int, int]:
    """
    Group a month's work by type, then by its number within that
    type: all four reels, then both stories. Ordered here rather
    than in SQL because ordering by an enum column depends on the
    database - see DELIVERABLE_TYPE_ORDER.
    """
    return type_rank(item.deliverable_type), item.position


def _party(workspace) -> RetainerParty:
    return RetainerParty(
        workspace_id=workspace.id,
        slug=workspace.slug,
        display_name=workspace.display_name,
    )


def _contact(user) -> Contact | None:
    if user is None:
        return None

    return Contact(
        name=f"{user.first_name} {user.last_name}".strip(),
        job_title=user.job_title,
        email=user.email,
        phone=user.phone,
    )


def deliverable_response(
    deliverable: RetainerDeliverable,
) -> DeliverableResponse:
    return DeliverableResponse.model_validate(deliverable)
