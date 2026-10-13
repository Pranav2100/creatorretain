from collections.abc import Callable
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.common.entitlements import Capability
from app.common.enums import (
    OCCUPYING_STATUSES,
    TERMINAL_STATUSES,
    DeliverableStatus,
    DeliverableType,
    RetainerStatus,
    ReviewDecision,
    WorkspaceType,
)
from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.permissions import WorkspacePermission
from app.common.utils.billing_periods import build_periods
from app.database.models.retainer import Retainer
from app.database.models.retainer_deliverable import (
    RetainerDeliverable,
)
from app.database.models.retainer_deliverable_spec import (
    RetainerDeliverableSpec,
)
from app.database.models.retainer_period import RetainerPeriod
from app.database.repositories.retainer import RetainerRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.services.workspace_member import (
    WorkspaceContext,
    WorkspaceMemberService,
)

# Which side of the agreement a workspace is on. Almost every rule
# in this module turns on this rather than on role alone: the brand
# signs and reviews, the creator accepts and delivers.
BRAND = "brand"
CREATOR = "creator"

MAX_SPECS = 10
MAX_QUANTITY_PER_SPEC = 60


class RetainerService:
    """
    Agreements, the months they produce, and the work inside them.

    Periods are never created in advance. `ensure_periods` works
    out which ones should exist as of a given day and creates the
    missing ones, and every read goes through it first. That one
    function is also the whole of the scheduled job this will grow
    later: a nightly worker calls it for each active retainer and
    the behaviour is identical, just earlier.
    """

    def __init__(
        self,
        repository: RetainerRepository,
        workspace_repository: WorkspaceRepository,
        member_service: WorkspaceMemberService,
        clock: Callable[[], date] | None = None,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.member_service = member_service

        # Injected so tests can move time without waiting for it.
        self.clock = clock or (lambda: datetime.now(timezone.utc).date())

    # ------------------------------------------------------------------
    # Period derivation - the part cron will call
    # ------------------------------------------------------------------

    def ensure_periods(
        self,
        retainer: Retainer,
        as_of: date | None = None,
    ) -> list[RetainerPeriod]:
        """
        Create whatever periods should exist by `as_of`, then return
        all of them in order.

        Safe to call as often as you like: it compares what the rule
        says should exist against what does, and only writes the
        difference.
        """
        as_of = as_of or self.clock()

        if retainer.status in TERMINAL_STATUSES:
            return self.repository.list_periods(retainer.id)

        # A paused retainer keeps the periods it has earned and
        # stops accruing new ones. Resuming does not back-fill the
        # gap, because nobody worked those months.
        if retainer.status == RetainerStatus.PAUSED:
            return self.repository.list_periods(retainer.id)

        if retainer.status != RetainerStatus.ACTIVE:
            return []

        expected = build_periods(
            start_date=retainer.start_date,
            as_of=as_of,
            end_date=retainer.end_date,
        )

        if not expected:
            return []

        offset = retainer.sequence_offset or 0
        existing = self.repository.existing_sequences(retainer.id)

        missing = [
            window
            for window in expected
            if window.sequence + offset not in existing
        ]

        if missing:
            for window in missing:
                period = RetainerPeriod(
                    retainer_id=retainer.id,
                    sequence=window.sequence + offset,
                    period_start=window.start,
                    period_end=window.end,
                    amount=retainer.monthly_amount,
                    currency=retainer.currency,
                )

                self.repository.add_period(period)
                self._expand_deliverables(period, retainer.specs)

            self.repository.commit()

        return self.repository.list_periods(retainer.id)

    @staticmethod
    def _expand_deliverables(
        period: RetainerPeriod,
        specs: list[RetainerDeliverableSpec],
    ) -> None:
        """
        Turn "4 reels" into four rows, so each can be submitted and
        reviewed on its own.
        """
        for spec in specs:
            for index in range(1, spec.quantity + 1):
                period.deliverables.append(
                    RetainerDeliverable(
                        deliverable_type=spec.deliverable_type,
                        position=index,
                        status=DeliverableStatus.PENDING,
                        title=spec.notes,
                    )
                )

    # ------------------------------------------------------------------
    # Creating an offer
    # ------------------------------------------------------------------

    def create(
        self,
        current_user_id: UUID,
        *,
        creator_workspace_id: UUID,
        title: str,
        monthly_amount: Decimal,
        deliverables: list[tuple[DeliverableType, int, str | None]],
        start_date: date | None = None,
        end_date: date | None = None,
        notice_period_days: int = 30,
        terms: str | None = None,
        message: str | None = None,
        currency: str = "INR",
    ) -> Retainer:
        context = self.member_service.resolve_context(current_user_id)
        context.require(
            WorkspacePermission.MANAGE_RETAINERS,
            "Only the workspace owner and admins can set up a "
            "retainer. Ask one of them to send it.",
        )
        context.require_capability(Capability.CREATE_RETAINER)

        # Pending offers count too. Otherwise a workspace at its
        # ceiling could send unlimited offers and simply wait.
        taken = self.repository.count_occupying(
            context.workspace_id,
            OCCUPYING_STATUSES,
        )
        context.require_within_limit(
            "active_retainers",
            taken,
            "active retainers",
        )

        creator_workspace = self.workspace_repository.get(
            creator_workspace_id,
        )

        if (
            creator_workspace is None
            or creator_workspace.deleted_at is not None
        ):
            raise NotFoundError("Creator not found.")

        # Checked before the type test, so hiring your own workspace
        # reads as "that is you" rather than the less useful
        # "not a creator".
        if creator_workspace.id == context.workspace_id:
            raise ConflictError(
                "You cannot put your own workspace on retainer."
            )

        if creator_workspace.workspace_type != WorkspaceType.CREATOR:
            raise ConflictError(
                "Retainers can only be offered to creators."
            )

        existing = self.repository.find_open_between(
            context.workspace_id,
            creator_workspace.id,
        )

        if existing is not None:
            raise ConflictError(
                "You already have a live retainer with this creator. "
                "End it before starting another."
            )

        self._validate_deliverables(deliverables)

        if monthly_amount <= 0:
            raise ConflictError(
                "The monthly amount must be more than zero."
            )

        start = start_date or self.clock()

        if end_date is not None and end_date <= start:
            raise ConflictError(
                "The end date must be after the start date."
            )

        retainer = Retainer(
            brand_workspace_id=context.workspace_id,
            creator_workspace_id=creator_workspace.id,
            created_by_user_id=current_user_id,
            title=title,
            status=RetainerStatus.PENDING,
            monthly_amount=monthly_amount,
            currency=currency,
            start_date=start,
            end_date=end_date,
            notice_period_days=notice_period_days,
            terms=terms,
            message=message,
        )

        for deliverable_type, quantity, notes in deliverables:
            retainer.specs.append(
                RetainerDeliverableSpec(
                    deliverable_type=deliverable_type,
                    quantity=quantity,
                    notes=notes,
                )
            )

        return self.repository.create(retainer)

    @staticmethod
    def _validate_deliverables(
        deliverables: list[tuple[DeliverableType, int, str | None]],
    ) -> None:
        if not deliverables:
            raise ConflictError(
                "A retainer needs at least one deliverable."
            )

        if len(deliverables) > MAX_SPECS:
            raise ConflictError(
                f"A retainer can have at most {MAX_SPECS} kinds of "
                "deliverable."
            )

        seen: set[DeliverableType] = set()

        for deliverable_type, quantity, _ in deliverables:
            if deliverable_type in seen:
                raise ConflictError(
                    f"{deliverable_type.value} is listed twice. "
                    "Combine them into one line with a quantity."
                )

            seen.add(deliverable_type)

            if quantity < 1:
                raise ConflictError(
                    "Every deliverable needs a quantity of at least 1."
                )

            if quantity > MAX_QUANTITY_PER_SPEC:
                raise ConflictError(
                    f"At most {MAX_QUANTITY_PER_SPEC} of one kind "
                    "per month."
                )

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def list_for_user(
        self,
        current_user_id: UUID,
        statuses: list[RetainerStatus] | None = None,
    ) -> tuple[list[Retainer], UUID]:
        context = self.member_service.resolve_context(current_user_id)
        context.require(
            WorkspacePermission.VIEW_RETAINERS,
            "You don't have permission to view retainers.",
        )

        retainers = self.repository.list_for_workspace(
            context.workspace_id,
            statuses,
        )

        for retainer in retainers:
            self.ensure_periods(retainer)

        return retainers, context.workspace_id

    def get(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> tuple[Retainer, str]:
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )

        self.ensure_periods(retainer)

        return self.repository.get_full(retainer.id) or retainer, side

    def periods(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> list[RetainerPeriod]:
        _, retainer, _ = self._resolve(current_user_id, retainer_id)

        return self.ensure_periods(retainer)

    # ------------------------------------------------------------------
    # Answering an offer
    # ------------------------------------------------------------------

    def accept(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> Retainer:
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )

        if side != CREATOR:
            raise PermissionDeniedError(
                "Only the creator can accept a retainer."
            )

        context.require(
            WorkspacePermission.MANAGE_RETAINERS,
            "Only the workspace owner and admins can accept a "
            "retainer.",
        )

        self._require_status(
            retainer,
            RetainerStatus.PENDING,
            "This retainer is no longer open to accept.",
        )

        now = self._now()
        today = self.clock()

        retainer.status = RetainerStatus.ACTIVE
        retainer.accepted_at = now
        retainer.responded_at = now

        # An offer made last week and accepted today starts today.
        # Back-dating would invent a month of work nobody agreed to.
        if retainer.start_date < today:
            retainer.start_date = today

        saved = self.repository.save(retainer)
        self.ensure_periods(saved)

        return self.repository.get_full(saved.id) or saved

    def decline(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        reason: str | None = None,
    ) -> Retainer:
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )

        if side != CREATOR:
            raise PermissionDeniedError(
                "Only the creator can decline a retainer."
            )

        context.require(WorkspacePermission.MANAGE_RETAINERS)

        self._require_status(
            retainer,
            RetainerStatus.PENDING,
            "This retainer is no longer open to decline.",
        )

        retainer.status = RetainerStatus.DECLINED
        retainer.responded_at = self._now()
        retainer.ended_reason = reason

        return self.repository.save(retainer)

    def cancel(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> Retainer:
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )

        if side != BRAND:
            raise PermissionDeniedError(
                "Only the workspace that sent the offer can "
                "withdraw it."
            )

        context.require(WorkspacePermission.MANAGE_RETAINERS)

        self._require_status(
            retainer,
            RetainerStatus.PENDING,
            "This retainer has already been answered. End it "
            "instead of withdrawing it.",
        )

        retainer.status = RetainerStatus.CANCELLED
        retainer.ended_at = self._now()

        return self.repository.save(retainer)

    # ------------------------------------------------------------------
    # Running it
    # ------------------------------------------------------------------

    def pause(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        reason: str | None = None,
    ) -> Retainer:
        context, retainer, _ = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        self._require_status(
            retainer,
            RetainerStatus.ACTIVE,
            "Only an active retainer can be paused.",
        )

        # Bring the record up to date before freezing it, so the
        # month in progress is not lost.
        self.ensure_periods(retainer)

        retainer.status = RetainerStatus.PAUSED
        retainer.paused_at = self._now()
        retainer.ended_reason = reason

        return self.repository.save(retainer)

    def resume(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> Retainer:
        context, retainer, _ = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        self._require_status(
            retainer,
            RetainerStatus.PAUSED,
            "This retainer is not paused.",
        )

        today = self.clock()
        used = self.repository.existing_sequences(retainer.id)

        # Resuming restarts the clock from today rather than
        # back-filling the paused months. The schedule shifts; the
        # creator is not suddenly owed work for a gap they agreed
        # to take off.
        retainer.status = RetainerStatus.ACTIVE
        retainer.paused_at = None
        retainer.ended_reason = None
        retainer.start_date = today

        # Numbering continues from the highest period already
        # earned, so the next one is 4 rather than a second 1.
        retainer.sequence_offset = max(used) if used else 0

        saved = self.repository.save(retainer)
        self.ensure_periods(saved)

        return self.repository.get_full(saved.id) or saved

    def end(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        reason: str | None = None,
    ) -> Retainer:
        context, retainer, _ = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        if retainer.status in TERMINAL_STATUSES:
            raise ConflictError("This retainer has already ended.")

        if retainer.status == RetainerStatus.PENDING:
            raise ConflictError(
                "This retainer has not started. Withdraw or decline "
                "it instead."
            )

        self.ensure_periods(retainer)

        retainer.status = RetainerStatus.ENDED
        retainer.ended_at = self._now()
        retainer.ended_reason = reason

        return self.repository.save(retainer)

    # ------------------------------------------------------------------
    # The work itself
    # ------------------------------------------------------------------

    def submit_deliverable(
        self,
        current_user_id: UUID,
        deliverable_id: UUID,
        *,
        url: str,
        note: str | None = None,
    ) -> RetainerDeliverable:
        context, deliverable, side = self._resolve_deliverable(
            current_user_id,
            deliverable_id,
        )

        if side != CREATOR:
            raise PermissionDeniedError(
                "Only the creator can submit work."
            )

        context.require(WorkspacePermission.MANAGE_RETAINERS)

        if deliverable.status == DeliverableStatus.APPROVED:
            raise ConflictError(
                "This deliverable has already been approved."
            )

        if deliverable.status == DeliverableStatus.REJECTED:
            raise ConflictError(
                "This deliverable was rejected and is closed."
            )

        # A submission is counted when the creator answers something:
        # the brief, or a request for changes. Sending a corrected
        # link while the first one is still waiting to be reviewed
        # is the same attempt, so a double click or a fixed typo
        # does not inflate the number the brand reads as "they got
        # it wrong twice".
        counts_as_attempt = deliverable.status in (
            DeliverableStatus.PENDING,
            DeliverableStatus.REVISION_REQUESTED,
        )

        deliverable.status = DeliverableStatus.SUBMITTED
        deliverable.submitted_url = url
        deliverable.submitted_note = note
        deliverable.submitted_at = self._now()

        if counts_as_attempt:
            deliverable.submission_count += 1

        # A resubmission answers the previous review, so the old
        # note should not sit there looking current.
        deliverable.review_note = None
        deliverable.reviewed_at = None
        deliverable.reviewed_by_user_id = None

        return self.repository.save_deliverable(deliverable)

    def review_deliverable(
        self,
        current_user_id: UUID,
        deliverable_id: UUID,
        *,
        decision: ReviewDecision,
        note: str | None = None,
    ) -> RetainerDeliverable:
        context, deliverable, side = self._resolve_deliverable(
            current_user_id,
            deliverable_id,
        )

        if side != BRAND:
            raise PermissionDeniedError(
                "Only the hiring workspace can review work."
            )

        context.require(WorkspacePermission.MANAGE_RETAINERS)

        if deliverable.status != DeliverableStatus.SUBMITTED:
            raise ConflictError(
                "There is nothing submitted to review."
            )

        if decision == ReviewDecision.REQUEST_REVISION and not note:
            raise ConflictError(
                "Say what needs changing when asking for a revision."
            )

        deliverable.status = decision.to_status()
        deliverable.review_note = note
        deliverable.reviewed_at = self._now()
        deliverable.reviewed_by_user_id = current_user_id

        return self.repository.save_deliverable(deliverable)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> tuple[WorkspaceContext, Retainer, str]:
        context = self.member_service.resolve_context(current_user_id)
        retainer = self.repository.get_full(retainer_id)

        if retainer is None:
            raise NotFoundError("Retainer not found.")

        side = self._side(context.workspace_id, retainer)

        if side is None:
            # Not "forbidden": a workspace has no business knowing
            # that someone else's retainer exists.
            raise NotFoundError("Retainer not found.")

        context.require(
            WorkspacePermission.VIEW_RETAINERS,
            "You don't have permission to view retainers.",
        )

        return context, retainer, side

    def _resolve_deliverable(
        self,
        current_user_id: UUID,
        deliverable_id: UUID,
    ) -> tuple[WorkspaceContext, RetainerDeliverable, str]:
        context = self.member_service.resolve_context(current_user_id)
        deliverable = self.repository.get_deliverable(deliverable_id)

        if deliverable is None:
            raise NotFoundError("Deliverable not found.")

        retainer = deliverable.period.retainer
        side = self._side(context.workspace_id, retainer)

        if side is None:
            raise NotFoundError("Deliverable not found.")

        if retainer.status != RetainerStatus.ACTIVE:
            raise ConflictError(
                "This retainer is not active, so its work cannot "
                "be changed."
            )

        return context, deliverable, side

    @staticmethod
    def _side(workspace_id: UUID, retainer: Retainer) -> str | None:
        if workspace_id == retainer.brand_workspace_id:
            return BRAND

        if workspace_id == retainer.creator_workspace_id:
            return CREATOR

        return None

    @staticmethod
    def _require_status(
        retainer: Retainer,
        expected: RetainerStatus,
        message: str,
    ) -> None:
        if retainer.status != expected:
            raise ConflictError(message)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)
