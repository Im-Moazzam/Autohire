import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.interview import InterviewSlot
from app.models.recruiter import Recruiter
from app.models.scheduling import SchedulingPreference
from app.schemas.common import PaginationParams
from app.schemas.enums import SlotStatus, SubmissionStatus, TaskStatus, TaskType
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
