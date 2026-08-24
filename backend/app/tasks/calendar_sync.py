"""CALENDAR_SYNC — generates interview slots for the candidates named at
enqueue time, in the order the recruiter submitted them, creates a Google
Calendar event per slot, and enqueues EMAIL_DISPATCH once the event exists.

Same shape as batch_ranking_job (docs/architecture.md): own SessionLocal(),
acks_late, scoped autoretry_for, terminal-state no-op for idempotent
re-delivery.

Per-candidate outcomes are data (result_summary), not exceptions — one
candidate having no available slot, an existing live slot, or a Calendar
failure never aborts the run for the rest (mirrors "one bad PDF must not
abort a 200-candidate run", US-16). The task only ends FAILED if the run
itself throws.

Ordering, as in US-06: the slot row commits first, *then* the calendar event
is created, *then* the row updates with the event id. No DB transaction is
held open across the Google call.
"""

import uuid
from datetime import UTC, datetime, timedelta

from celery import Task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.adapters.calendar_store import get_calendar_store
from app.core.db import SessionLocal
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.enums import SlotStatus, SubmissionStatus, TaskStatus
from app.services.interview_service import (
    HORIZON_DAYS,
    generate_slots,
    get_preferences_row,
    occupied_intervals,
)
from app.tasks.email_dispatch import email_dispatch_job
from app.worker import celery_app

_RETRYABLE = (OperationalError,)


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=3,
    soft_time_limit=300,
    retry_backoff=True,
    autoretry_for=_RETRYABLE,
)
def calendar_sync_job(self: Task, task_id: str, candidate_ids: list[str]) -> None:
    with SessionLocal() as db:
        task = db.get(BackgroundTask, uuid.UUID(task_id))
        if task is None:
            return
        if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
            return

        task.status = TaskStatus.RUNNING
        db.commit()

        try:
            summary = _run_calendar_sync(db, task, [uuid.UUID(cid) for cid in candidate_ids])
        except (SoftTimeLimitExceeded, Retry):
            raise
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now(UTC)
            db.commit()
            raise

        task.status = TaskStatus.SUCCESS
        task.result_summary = summary
        task.completed_at = datetime.now(UTC)
        db.commit()


def _unique_violation_reason(exc: IntegrityError) -> str:
    """Two partial-unique indexes can raise IntegrityError here (TS-06/R-10):
    uq_interview_slots_candidate_live (this candidate already has a live
    slot) and uq_interview_slots_recruiter_time (two different candidates
    collided on the exact same recruiter+instant). Inspect which one fired
    rather than hard-coding a single reason — falls back to
    ALREADY_SCHEDULED if the driver doesn't expose a constraint name."""
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None) or ""
    if "recruiter_time" in constraint_name:
        return "SLOT_TIME_TAKEN"
    return "ALREADY_SCHEDULED"


def _run_calendar_sync(db: Session, task: BackgroundTask, candidate_ids: list[uuid.UUID]) -> dict:
    assert task.job_id is not None
    job = db.get(JobPosting, task.job_id)
    assert job is not None

    pref = get_preferences_row(db, task.recruiter_id)
    assert pref is not None  # enqueue_scheduling already required this to exist

    recruiter = db.get(Recruiter, task.recruiter_id)
    assert recruiter is not None

    calendar_store = get_calendar_store()

    now = datetime.now(UTC)
    horizon_end = now + timedelta(days=HORIZON_DAYS)
    occupied = occupied_intervals(db, task.recruiter_id, now, horizon_end)

    candidates_by_id = {
        c.candidate_id: c
        for c in db.scalars(
            select(Candidate).where(
                Candidate.candidate_id.in_(candidate_ids),
                Candidate.job_id == job.job_id,
                Candidate.deleted_at.is_(None),
            )
        ).all()
    }

    scheduled = 0
    unscheduled: list[dict] = []

    for candidate_id in candidate_ids:
        candidate = candidates_by_id.get(candidate_id)
        if candidate is None:
            unscheduled.append(
                {
                    "candidate_id": str(candidate_id),
                    "full_name": None,
                    "reason": "CANDIDATE_NOT_FOUND",
                }
            )
            continue
        if candidate.submission_status != SubmissionStatus.RANKED:
            # Rare race: status changed between enqueue and this task running.
            unscheduled.append(
                {
                    "candidate_id": str(candidate_id),
                    "full_name": candidate.full_name,
                    "reason": "NOT_RANKED",
                }
            )
            continue

        times = generate_slots(pref, occupied, count=1, now=now)
        if not times:
            unscheduled.append(
                {
                    "candidate_id": str(candidate_id),
                    "full_name": candidate.full_name,
                    "reason": "NO_SLOT_IN_HORIZON",
                }
            )
            continue
        scheduled_at = times[0]

        slot = InterviewSlot(
            candidate_id=candidate.candidate_id,
            job_id=job.job_id,
            recruiter_id=task.recruiter_id,
            scheduled_at=scheduled_at,
            duration_minutes=pref.slot_duration_minutes,
            status=SlotStatus.PENDING,
        )
        db.add(slot)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            unscheduled.append(
                {
                    "candidate_id": str(candidate_id),
                    "full_name": candidate.full_name,
                    "reason": _unique_violation_reason(exc),
                }
            )
            continue
        db.refresh(slot)

        occupied = [
            *occupied,
            (scheduled_at, scheduled_at + timedelta(minutes=pref.slot_duration_minutes)),
        ]

        try:
            event = calendar_store.create_event(
                recruiter,
                summary=f"Interview: {candidate.full_name} — {job.job_title}",
                description=job.job_description,
                starts_at=scheduled_at,
                duration_minutes=pref.slot_duration_minutes,
                attendee_email=candidate.email,
            )
        except Exception:
            # Slot row stays PENDING with no event id — present and retryable,
            # never a candidate marked INVITED with no interview (TC-05).
            unscheduled.append(
                {
                    "candidate_id": str(candidate_id),
                    "full_name": candidate.full_name,
                    "reason": "CALENDAR_FAILED",
                }
            )
            continue

        slot.google_calendar_event_id = event.event_id
        slot.google_meet_link = event.meet_link
        candidate.submission_status = SubmissionStatus.INVITED
        db.commit()
        scheduled += 1

        email_dispatch_job.delay(str(slot.slot_id))

    return {"scheduled": scheduled, "unscheduled": unscheduled, "horizon_days": HORIZON_DAYS}
