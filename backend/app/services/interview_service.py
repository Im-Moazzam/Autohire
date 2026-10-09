import contextlib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.calendar_store import get_calendar_store
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.models.scheduling import SchedulingPreference
from app.schemas.common import PaginationParams
from app.schemas.enums import EmailType, SlotStatus, SubmissionStatus, TaskStatus, TaskType
from app.services.task_service import active_task_for_job

HORIZON_DAYS = 14

_JOB_NOT_FOUND = {"code": "JOB_NOT_FOUND", "message": "Job not found."}
_CANDIDATE_NOT_FOUND = {"code": "CANDIDATE_NOT_FOUND", "message": "Candidate not found."}
_INVALID_CANDIDATE_STATUS = {
    "code": "INVALID_CANDIDATE_STATUS",
    "message": "Only RANKED candidates can be scheduled.",
}
_NO_PREFERENCES = {
    "code": "NO_SCHEDULING_PREFERENCES",
    "message": "Set your availability before scheduling interviews.",
}
_PROCESSING_IN_PROGRESS = {
    "code": "PROCESSING_IN_PROGRESS",
    "message": "A processing task for this job is already running.",
}
_SLOT_NOT_FOUND = {"code": "SLOT_NOT_FOUND", "message": "Interview slot not found."}
_INVALID_STATE_TRANSITION = {
    "code": "INVALID_STATE_TRANSITION",
    "message": "This interview can no longer be cancelled.",
}

# Only a live slot can be cancelled; CANCELLED/DECLINED/RESCHEDULED are
# already terminal for this action (US-28).
_LEGAL_SLOT_TRANSITIONS: dict[SlotStatus, set[SlotStatus]] = {
    SlotStatus.PENDING: {SlotStatus.CANCELLED},
    SlotStatus.CONFIRMED: {SlotStatus.CANCELLED},
    SlotStatus.DECLINED: set(),
    SlotStatus.RESCHEDULED: set(),
    SlotStatus.CANCELLED: set(),
}


def is_legal_slot_transition(current: SlotStatus, target: SlotStatus) -> bool:
    """Unlike job_service's transition check, current == target is NOT an
    automatic pass here: re-cancelling an already-CANCELLED slot must 409,
    not silently re-run the rebook/email side effects a second time."""
    return target in _LEGAL_SLOT_TRANSITIONS[current]


_WEEKDAY_INDEX = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def _overlaps(
    start: datetime, end: datetime, occupied: Sequence[tuple[datetime, datetime]]
) -> bool:
    return any(start < o_end and o_start < end for o_start, o_end in occupied)


def generate_slots(
    pref: SchedulingPreference,
    occupied: Sequence[tuple[datetime, datetime]],
    count: int,
    now: datetime,
    horizon_days: int = HORIZON_DAYS,
) -> list[datetime]:
    """Available start times honouring pref: available_days, the
    start/end-time window, slot_duration_minutes apart, starting from the
    next available day.

    ZoneInfo(pref.timezone) — never settings.scheduling_timezone directly
    (ADR-005). The row records the zone it was entered in; the live setting
    is only correct for a row that doesn't exist yet.

    `occupied` is a list of [start, end) intervals already booked (each
    using the *existing* row's own duration, not this preference's) —
    checked by overlap, not exact-timestamp equality, since a recruiter can
    change slot_duration_minutes between runs and a plain "taken" set of
    start times would miss the resulting overlap.

    Returns up to `count` UTC-aware start times, earliest first.
    """
    tz = ZoneInfo(pref.timezone)
    duration = timedelta(minutes=pref.slot_duration_minutes)
    now_local = now.astimezone(tz)
    available_days = {_WEEKDAY_INDEX[day] for day in pref.available_days}

    found: list[datetime] = []
    day = now_local.date()
    for _ in range(horizon_days):
        if day.weekday() in available_days:
            cursor = datetime.combine(day, pref.available_start_time, tzinfo=tz)
            window_end = datetime.combine(day, pref.available_end_time, tzinfo=tz)
            while cursor + duration <= window_end:
                slot_end = cursor + duration
                if cursor >= now_local and not _overlaps(cursor, slot_end, occupied):
                    found.append(cursor.astimezone(UTC))
                    if len(found) >= count:
                        return found
                cursor += duration
        day += timedelta(days=1)
    return found


def get_preferences_row(db: Session, recruiter_id: uuid.UUID) -> SchedulingPreference | None:
    return db.scalar(
        select(SchedulingPreference).where(SchedulingPreference.recruiter_id == recruiter_id)
    )


def occupied_intervals(
    db: Session, recruiter_id: uuid.UUID, horizon_start: datetime, horizon_end: datetime
) -> list[tuple[datetime, datetime]]:
    """Every live (PENDING/CONFIRMED) slot for this recruiter overlapping the
    horizon, as [start, start + its own duration_minutes) — see
    generate_slots' docstring for why the duration must be the existing
    row's, not the current preference's."""
    rows = db.execute(
        select(InterviewSlot.scheduled_at, InterviewSlot.duration_minutes).where(
            InterviewSlot.recruiter_id == recruiter_id,
            InterviewSlot.status.in_([SlotStatus.PENDING, SlotStatus.CONFIRMED]),
            InterviewSlot.scheduled_at < horizon_end,
            InterviewSlot.scheduled_at >= horizon_start,
        )
    ).all()
    return [
        (scheduled_at, scheduled_at + timedelta(minutes=duration))
        for scheduled_at, duration in rows
    ]


def enqueue_scheduling(
    db: Session, recruiter: Recruiter, job_id: uuid.UUID, candidate_ids: Sequence[uuid.UUID]
) -> BackgroundTask:
    """Synchronous validation, then the same enqueue shape as
    enqueue_batch_ranking: commit the PENDING row before .delay(), IntegrityError
    backstop. NO_SCHEDULING_PREFERENCES is checked here rather than inside the
    task so the recruiter gets an actionable 409 immediately instead of a task
    that fails after the fact (TC-06)."""
    from app.services import job_service  # local import: avoids a service-to-service cycle
    from app.tasks.calendar_sync import calendar_sync_job

    job = job_service.get_job(db, recruiter.recruiter_id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_JOB_NOT_FOUND)

    if active_task_for_job(db, job.job_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PROCESSING_IN_PROGRESS)

    candidates_by_id = {
        c.candidate_id: c
        for c in db.scalars(
            select(Candidate).where(
                Candidate.job_id == job.job_id,
                Candidate.candidate_id.in_(candidate_ids),
                Candidate.deleted_at.is_(None),
            )
        ).all()
    }
    if set(candidate_ids) - candidates_by_id.keys():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_CANDIDATE_NOT_FOUND)

    if any(
        candidates_by_id[cid].submission_status != SubmissionStatus.RANKED for cid in candidate_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_INVALID_CANDIDATE_STATUS
        )

    if get_preferences_row(db, recruiter.recruiter_id) is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NO_PREFERENCES)

    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id,
        job_id=job.job_id,
        task_type=TaskType.CALENDAR_SYNC,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_PROCESSING_IN_PROGRESS
        ) from None
    db.refresh(task)

    # Order preserved exactly as the recruiter submitted it — that ordering
    # is their intent about who gets the earlier slots.
    async_result = calendar_sync_job.delay(str(task.task_id), [str(cid) for cid in candidate_ids])
    task.celery_task_id = async_result.id
    db.commit()
    db.refresh(task)
    return task


def list_slots(
    db: Session,
    recruiter_id: uuid.UUID,
    params: PaginationParams,
    job_id: uuid.UUID | None,
    status_filter: SlotStatus | None,
) -> tuple[list[InterviewSlot], int]:
    base = select(InterviewSlot).where(InterviewSlot.recruiter_id == recruiter_id)
    if job_id is not None:
        base = base.where(InterviewSlot.job_id == job_id)
    if status_filter is not None:
        base = base.where(InterviewSlot.status == status_filter)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(InterviewSlot.scheduled_at)
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return list(rows), total


def available_slots_for_recruiter(
    db: Session, recruiter_id: uuid.UUID, count: int
) -> list[tuple[datetime, datetime]]:
    """Backs GET /scheduling/available-slots — a preview of the next `count`
    [start, end) windows, computed the same way the CALENDAR_SYNC task would
    pick them. Synthesized defaults (no saved preferences row) are not valid
    here: the recruiter must have actually set availability before this is
    meaningful."""
    pref = get_preferences_row(db, recruiter_id)
    if pref is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NO_PREFERENCES)
    now = datetime.now(UTC)
    horizon_end = now + timedelta(days=HORIZON_DAYS)
    occupied = occupied_intervals(db, recruiter_id, now, horizon_end)
    starts = generate_slots(pref, occupied, count, now)
    duration = timedelta(minutes=pref.slot_duration_minutes)
    return [(start, start + duration) for start in starts]


def cancel_slot(
    db: Session, recruiter: Recruiter, slot_id: uuid.UUID, reschedule_reason: str | None
) -> InterviewSlot:
    """PATCH /interviews/{slot_id} with status=CANCELLED (US-28). Cancels the
    slot, deletes its Calendar event, then tries to auto-book the candidate's
    next available slot — same generate_slots/occupied_intervals path
    calendar_sync_job uses. No replacement found in the horizon: the slot
    stays CANCELLED with no new row, and the candidate gets a
    cancellation-only email instead of a reschedule one.

    Returns the replacement slot if one was created, otherwise the cancelled
    slot itself — either way, the row the recruiter should see as "what
    happened to this interview."
    """
    from app.tasks.email_dispatch import email_dispatch_job  # avoids a service<->task cycle

    slot = db.get(InterviewSlot, slot_id)
    if slot is None or slot.recruiter_id != recruiter.recruiter_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SLOT_NOT_FOUND)
    if not is_legal_slot_transition(slot.status, SlotStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_INVALID_STATE_TRANSITION)

    old_event_id = slot.google_calendar_event_id
    slot.status = SlotStatus.CANCELLED
    if reschedule_reason is not None:
        slot.reschedule_reason = reschedule_reason
    db.commit()
    db.refresh(slot)

    if old_event_id:
        # Cancellation already committed; a stale Calendar event is a
        # cosmetic loose end, never a reason to fail this request.
        with contextlib.suppress(Exception):
            get_calendar_store().delete_event(recruiter, old_event_id)

    new_slot = _try_rebook(db, recruiter, slot)
    if new_slot is not None:
        email_dispatch_job.delay(str(new_slot.slot_id), EmailType.INTERVIEW_RESCHEDULE.value)
        return new_slot

    email_dispatch_job.delay(str(slot.slot_id), EmailType.CANCELLATION.value)
    return slot


def _try_rebook(
    db: Session, recruiter: Recruiter, cancelled_slot: InterviewSlot
) -> InterviewSlot | None:
    pref = get_preferences_row(db, recruiter.recruiter_id)
    if pref is None:
        return None

    now = datetime.now(UTC)
    horizon_end = now + timedelta(days=HORIZON_DAYS)
    occupied = occupied_intervals(db, recruiter.recruiter_id, now, horizon_end)
    times = generate_slots(pref, occupied, count=1, now=now)
    if not times:
        return None

    new_slot = InterviewSlot(
        candidate_id=cancelled_slot.candidate_id,
        job_id=cancelled_slot.job_id,
        recruiter_id=recruiter.recruiter_id,
        scheduled_at=times[0],
        duration_minutes=pref.slot_duration_minutes,
        status=SlotStatus.PENDING,
    )
    db.add(new_slot)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race for this time slot — leave the cancellation as-is
        # rather than retrying inline; the recruiter can re-run from the UI.
        db.rollback()
        return None
    db.refresh(new_slot)

    candidate = db.get(Candidate, new_slot.candidate_id)
    job = db.get(JobPosting, new_slot.job_id)
    assert candidate is not None and job is not None  # FKs guarantee this

    try:
        event = get_calendar_store().create_event(
            recruiter,
            summary=f"Interview: {candidate.full_name} — {job.job_title}",
            description=job.job_description,
            starts_at=new_slot.scheduled_at,
            duration_minutes=new_slot.duration_minutes,
            attendee_email=candidate.email,
        )
        new_slot.google_calendar_event_id = event.event_id
        new_slot.google_meet_link = event.meet_link
        db.commit()
    except Exception:
        # Row stays PENDING without an event id — present and retryable,
        # same rule as calendar_sync_job.
        pass

    return new_slot
