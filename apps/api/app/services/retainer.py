from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.common.entitlements import Capability
from app.common.enums import (
    OCCUPYING_STATUSES,
    TERMINAL_STATUSES,
    DeliverableStatus,
    DeliverableType,
    RetainerEventKind,
    RetainerRequest,
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
from app.database.models.retainer_assignment import (
    RetainerAssignment,
)
from app.database.models.retainer_event import RetainerEvent
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

# What a request looks like in the history, asked and answered.
# Two tables rather than one with a branch in it, because asking
# and agreeing are different lines for a reader: "Nina asked to
# pause this" and then, later, "TalentX agreed - paused".
_ASKED = {
    RetainerRequest.PAUSE: RetainerEventKind.PAUSE_REQUESTED,
    RetainerRequest.RESUME: RetainerEventKind.RESUME_REQUESTED,
}

_HAPPENED = {
    RetainerRequest.PAUSE: RetainerEventKind.PAUSED,
    RetainerRequest.RESUME: RetainerEventKind.RESUMED,
}

# Asking for changes and rejecting stay separate: one invites a
# second attempt, the other closes the deliverable, and a history
# that blurs them cannot answer why the work stopped.
_REVIEWED = {
    ReviewDecision.APPROVE: RetainerEventKind.WORK_APPROVED,
    ReviewDecision.REQUEST_REVISION: (
        RetainerEventKind.CHANGES_REQUESTED
    ),
    ReviewDecision.REJECT: RetainerEventKind.WORK_REJECTED,
}


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
            self.clock(),
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

        saved = self.repository.create(retainer)

        # After the insert, not before: the id this event points at
        # does not exist until the row does.
        self._record(
            saved,
            RetainerEventKind.OFFERED,
            context=context,
            actor_user_id=current_user_id,
            side=BRAND,
            note=message,
        )
        self.repository.commit()

        return saved

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
            only_assigned_to=self._narrowed_to(
                context, current_user_id
            ),
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

        self._record(
            retainer,
            RetainerEventKind.ACCEPTED,
            context=context,
            actor_user_id=current_user_id,
            side=side,
        )

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

        self._record(
            retainer,
            RetainerEventKind.DECLINED,
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=reason,
        )

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

        self._record(
            retainer,
            RetainerEventKind.OFFER_WITHDRAWN,
            context=context,
            actor_user_id=current_user_id,
            side=side,
        )

        return self.repository.save(retainer)

    # ------------------------------------------------------------------
    # Running it
    # ------------------------------------------------------------------

    def request_change(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        *,
        action: RetainerRequest,
        reason: str | None = None,
    ) -> Retainer:
        """
        Asks the other side for a pause or a resume.

        Nothing changes here except that a question is now on the
        table. Pausing stops the months accruing and therefore the
        money, so it is not one party's to do alone.
        """
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        if retainer.pending_action is not None:
            raise ConflictError(
                "There is already a request waiting on an answer."
            )

        self._require_status(
            retainer,
            action.requires_status,
            "Only an active retainer can be paused."
            if action == RetainerRequest.PAUSE
            else "This retainer is not paused.",
        )

        retainer.pending_action = action
        retainer.pending_by_side = side
        retainer.pending_by_user_id = current_user_id
        retainer.pending_at = self._now()
        retainer.pending_reason = reason

        self._record(
            retainer,
            _ASKED[action],
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=reason,
        )

        return self.repository.save(retainer)

    def approve_change(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> Retainer:
        """The other side says yes, and only then does it happen."""
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        action = self._pending_for_answer(retainer, side)

        # Recorded before applying, because applying clears the
        # reason the other side gave and this event carries it.
        self._record(
            retainer,
            _HAPPENED[action],
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=retainer.pending_reason,
        )

        if action == RetainerRequest.PAUSE:
            return self._apply_pause(retainer)

        return self._apply_resume(retainer)

    def reject_change(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        reason: str | None = None,
    ) -> Retainer:
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        self._pending_for_answer(retainer, side)

        self._record(
            retainer,
            RetainerEventKind.REQUEST_REJECTED,
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=reason,
        )

        self._clear_pending(retainer)

        return self.repository.save(retainer)

    def withdraw_change(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> Retainer:
        """Taking back your own request before it is answered."""
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(WorkspacePermission.MANAGE_RETAINERS)

        if retainer.pending_action is None:
            raise ConflictError("There is nothing waiting.")

        if retainer.pending_by_side != side:
            raise PermissionDeniedError(
                "That request is not yours to withdraw."
            )

        self._record(
            retainer,
            RetainerEventKind.REQUEST_WITHDRAWN,
            context=context,
            actor_user_id=current_user_id,
            side=side,
        )

        self._clear_pending(retainer)

        return self.repository.save(retainer)

    def _pending_for_answer(
        self,
        retainer: Retainer,
        side: str,
    ) -> RetainerRequest:
        """
        The request this side is entitled to answer.

        Approving your own request would make approval meaningless,
        so the side that asked is sent to withdraw instead.
        """
        if retainer.pending_action is None:
            raise ConflictError("There is nothing waiting on you.")

        if retainer.pending_by_side == side:
            raise ConflictError(
                "You asked for this. Withdraw it instead, or wait "
                "for an answer."
            )

        return retainer.pending_action

    @staticmethod
    def _clear_pending(retainer: Retainer) -> None:
        retainer.pending_action = None
        retainer.pending_by_side = None
        retainer.pending_by_user_id = None
        retainer.pending_at = None
        retainer.pending_reason = None

    def _apply_pause(self, retainer: Retainer) -> Retainer:
        # Bring the record up to date before freezing it, so the
        # month in progress is not lost.
        self.ensure_periods(retainer)

        retainer.status = RetainerStatus.PAUSED
        retainer.paused_at = self._now()
        retainer.ended_reason = retainer.pending_reason

        self._clear_pending(retainer)

        return self.repository.save(retainer)

    def _apply_resume(self, retainer: Retainer) -> Retainer:
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

        self._clear_pending(retainer)

        saved = self.repository.save(retainer)
        self.ensure_periods(saved)

        return self.repository.get_full(saved.id) or saved

    def end(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        reason: str | None = None,
    ) -> Retainer:
        context, retainer, side = self._resolve(
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

        if retainer.notice_given_at is not None:
            raise ConflictError(
                "Notice has already been given on this retainer."
            )

        self.ensure_periods(retainer)

        today = self.clock()

        # Notice rather than permission. Needing the other side to
        # agree would let either of them refuse forever, and the
        # length of the wind-down was already agreed when this was
        # signed - which is exactly what a notice period is for.
        finishes = today + timedelta(days=retainer.notice_period_days)

        retainer.end_date = finishes
        retainer.notice_given_at = self._now()
        retainer.notice_given_by_side = side
        retainer.ended_reason = reason

        # A request waiting on an answer is moot once someone is
        # walking away from the whole thing.
        self._clear_pending(retainer)

        self._record(
            retainer,
            RetainerEventKind.NOTICE_GIVEN,
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=reason,
            subject=finishes.isoformat(),
        )

        # Zero notice means it is over today, so record that now
        # rather than leaving it to be derived.
        if retainer.notice_period_days == 0:
            retainer.status = RetainerStatus.ENDED
            retainer.ended_at = self._now()

            self._record(
                retainer,
                RetainerEventKind.ENDED,
                context=context,
                actor_user_id=current_user_id,
                side=side,
            )

        saved = self.repository.save(retainer)

        return self.repository.get_full(saved.id) or saved

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

        self._record(
            deliverable.period.retainer,
            RetainerEventKind.WORK_SUBMITTED,
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=note,
            subject=self._deliverable_label(deliverable),
        )

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

        self._record(
            deliverable.period.retainer,
            _REVIEWED[decision],
            context=context,
            actor_user_id=current_user_id,
            side=side,
            note=note,
            subject=self._deliverable_label(deliverable),
        )

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

        # The same rule the list is filtered by, applied to the
        # single read. Both are needed and they have to agree: a
        # filtered list with an unguarded detail route is a list
        # that only looks private, since the ids are guessable
        # from anywhere else they appear.
        narrowed = self._narrowed_to(context, current_user_id)

        if narrowed is not None and not self.repository.is_assigned(
            retainer.id,
            narrowed,
        ):
            # Not found rather than forbidden, for the same reason
            # as above: "you may not see this one" still tells
            # somebody it is there.
            raise NotFoundError("Retainer not found.")

        return context, retainer, side

    @staticmethod
    def _narrowed_to(
        context: WorkspaceContext,
        current_user_id: UUID,
    ) -> UUID | None:
        """
        Whose assignments to filter by, or None to see everything.

        Written as a permission the seniors hold rather than as a
        role check, so a role added later starts out narrow and
        somebody has to decide to widen it. The failure that
        matters here is the one where a new role silently sees the
        whole agency.
        """
        if context.allows(WorkspacePermission.VIEW_ALL_RETAINERS):
            return None

        return current_user_id

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

        # A deliverable is reachable by its own id, so the rule
        # that hides a retainer has to hide its work too -
        # otherwise the front door is locked and the window is
        # open.
        narrowed = self._narrowed_to(context, current_user_id)

        if narrowed is not None and not self.repository.is_assigned(
            retainer.id,
            narrowed,
        ):
            raise NotFoundError("Deliverable not found.")

        if retainer.status != RetainerStatus.ACTIVE:
            raise ConflictError(
                "This retainer is not active, so its work cannot "
                "be changed."
            )

        return context, deliverable, side

    # ------------------------------------------------------------------
    # Who runs this account
    # ------------------------------------------------------------------

    def assignees(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> list[RetainerAssignment]:
        """Everyone put on this retainer, for anyone who can see it."""
        self._resolve(current_user_id, retainer_id)

        return self.repository.assignments_for(retainer_id)

    def assign(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        user_id: UUID,
    ) -> list[RetainerAssignment]:
        """
        Puts somebody on an account.

        Only the hiring side assigns: a retainer is one agreement
        but two organisations, and who runs it inside the agency
        is not the creator's business - nor is the creator's staff
        the agency's.
        """
        context, retainer, side = self._resolve(
            current_user_id,
            retainer_id,
        )
        context.require(
            WorkspacePermission.ASSIGN_RETAINERS,
            "Only the workspace owner and admins decide who runs "
            "an account.",
        )

        member = self.member_service.get_active_membership(user_id)

        if member is None or member.workspace_id != context.workspace_id:
            # Said as "not on your team" rather than "no such
            # user", because the second one answers a question
            # nobody asked about who exists elsewhere.
            raise NotFoundError(
                "That person is not on your team."
            )

        existing = self.repository.get_assignment(retainer_id, user_id)

        if existing is not None:
            # Revived rather than inserted again: the unique
            # constraint is on the pair, so putting somebody back
            # on an account they used to run would otherwise
            # collide with their old row.
            if existing.deleted_at is None:
                return self.repository.assignments_for(retainer_id)

            existing.deleted_at = None
            existing.assigned_by_user_id = current_user_id
            self.repository.save(existing)
        else:
            self.repository.record_assignment(
                RetainerAssignment(
                    retainer_id=retainer_id,
                    user_id=user_id,
                    assigned_by_user_id=current_user_id,
                )
            )
            self.repository.commit()

        return self.repository.assignments_for(retainer_id)

    def unassign(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
        user_id: UUID,
    ) -> list[RetainerAssignment]:
        """
        Takes somebody off an account.

        Kept as a soft delete so the record of who used to run
        this survives - the same reason the history exists. The
        person loses sight of it either way.
        """
        context, _, _ = self._resolve(current_user_id, retainer_id)
        context.require(
            WorkspacePermission.ASSIGN_RETAINERS,
            "Only the workspace owner and admins decide who runs "
            "an account.",
        )

        existing = self.repository.get_assignment(retainer_id, user_id)

        if existing is None or existing.deleted_at is not None:
            raise NotFoundError(
                "That person is not on this retainer."
            )

        existing.deleted_at = self._now()
        self.repository.save(existing)

        return self.repository.assignments_for(retainer_id)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _record(
        self,
        retainer: Retainer,
        kind: RetainerEventKind,
        *,
        context: WorkspaceContext | None = None,
        actor_user_id: UUID | None = None,
        side: str | None = None,
        note: str | None = None,
        subject: str | None = None,
    ) -> RetainerEvent:
        """
        Writes one line of history, staged against the change that
        caused it.

        Called before the save rather than after, so the event and
        the change it describes are the same transaction. The name
        is copied in from the workspace as it reads today - see the
        model for why it is not looked up later.
        """
        event = RetainerEvent(
            retainer_id=retainer.id,
            kind=kind,
            actor_user_id=actor_user_id,
            actor_name=(
                context.workspace.display_name if context else None
            ),
            actor_side=side,
            note=(note.strip() or None) if note else None,
            subject=subject,
        )

        return self.repository.record(event)

    @staticmethod
    def _deliverable_label(deliverable: RetainerDeliverable) -> str:
        """
        "Reel #2" - the same handle the page puts on it, so the
        history and the month above it name the same thing.
        """
        return (
            f"{deliverable.deliverable_type.value.title()} "
            f"#{deliverable.position}"
        )

    def history(
        self,
        current_user_id: UUID,
        retainer_id: UUID,
    ) -> tuple[list[RetainerEvent], str]:
        """
        Everything that has happened, with the side asking.

        The side comes back because the same event is worded two
        ways - "you asked" against "they asked" - and the caller
        cannot work that out from the events alone.
        """
        _, _, side = self._resolve(current_user_id, retainer_id)

        return self.repository.events_for(retainer_id), side

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
