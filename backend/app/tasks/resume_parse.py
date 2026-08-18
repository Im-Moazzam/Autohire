"""RESUME_PARSE — one batch task per job, not one Celery task per candidate
(docs/drift.md): every AC/TC in the story describes a single background_tasks
row per job, fanning out over that job's candidates in-process instead.

Opens its own DB session (never one passed in from a request) — same rule
adapters/google/session.py follows, so a caller's transaction never gets
tangled with a worker's.
"""

import uuid
from datetime import UTC, datetime

import httpx
from celery import Task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.adapters.resume_store import get_resume_store
from app.core.db import SessionLocal
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.recruiter import Recruiter
from app.schemas.enums import SubmissionStatus, TaskStatus
from app.services.resume_parser import ExtractionFailed, extract_text
from app.services.resume_validation import sniff_extension
from app.worker import celery_app

# Only transient infrastructure failures autoretry — every per-candidate
# failure is already handled in-loop (below) and never propagates, so
# retrying on anything broader would redo a batch that already marked
# several candidates PARSE_ERROR.
_RETRYABLE = (OperationalError, httpx.TransportError)


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=3,
    soft_time_limit=300,
    retry_backoff=True,
    autoretry_for=_RETRYABLE,
)
def resume_parse_job(self: Task, task_id: str) -> None:
    with SessionLocal() as db:
        task = db.get(BackgroundTask, uuid.UUID(task_id))
        if task is None:
            return
        if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
            # Idempotency (TC-07): a re-delivered/re-run task with the same
            # task_id is a no-op once it has already reached a terminal state.
            return

        task.status = TaskStatus.RUNNING
        db.commit()

        try:
            _process_job_candidates(db, task)
        except (SoftTimeLimitExceeded, Retry):
            # Never let these reach the general handler below — they are
            # control-flow signals from Celery, not this candidate's fault.
            raise
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now(UTC)
            db.commit()
            raise

        task.status = TaskStatus.SUCCESS
        task.completed_at = datetime.now(UTC)
        db.commit()


def _process_job_candidates(db: Session, task: BackgroundTask) -> None:
    assert task.job_id is not None
    recruiter = db.get(Recruiter, task.recruiter_id)
    assert recruiter is not None
    store = get_resume_store()

    candidates = db.scalars(
        select(Candidate).where(
            Candidate.job_id == task.job_id,
            Candidate.deleted_at.is_(None),
            Candidate.submission_status.in_(
                [SubmissionStatus.SUBMITTED, SubmissionStatus.PARSE_ERROR]
            ),
        )
    ).all()

    for candidate in candidates:
        # Each candidate commits on its own — one bad resume must never abort
        # or roll back the rest of the batch (TC-05, the story's headline AC).
        try:
            content = store.fetch_resume(recruiter, candidate)
            ext = sniff_extension(content)
            if ext is None:
                raise ExtractionFailed("unrecognized file type")
            text = extract_text(content, ext)
        except (SoftTimeLimitExceeded, Retry):
            raise
        except Exception as exc:
            candidate.submission_status = SubmissionStatus.PARSE_ERROR
            candidate.parse_error = str(exc)
            db.commit()
            continue

        candidate.resume_text = text
        candidate.parse_error = None
        candidate.submission_status = SubmissionStatus.PARSED
        db.commit()
