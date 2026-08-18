"""RESUME_PARSE — one batch task per job, not one Celery task per candidate
(docs/drift.md): every AC/TC in the story describes a single background_tasks
row per job, fanning out over that job's candidates in-process instead.

Opens its own DB session (never one passed in from a request) — same rule
adapters/google/session.py follows, so a caller's transaction never gets
tangled with a worker's.

Commit 1 (task plumbing): the per-candidate body is a placeholder — no
resume is fetched or parsed yet. Commit 2 replaces _process_job_candidates
with real extraction (docs/stories/US-15-16.md).
"""

import uuid
from datetime import UTC, datetime

from celery import Task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.background_task import BackgroundTask
from app.schemas.enums import TaskStatus
from app.worker import celery_app

# Only transient infrastructure failures autoretry — every per-candidate
# failure is handled in-loop (commit 2) and never propagates, so retrying on
# anything broader would redo a batch that already marked candidates failed.
_RETRYABLE = (OperationalError,)


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
            # control-flow signals from Celery, not a candidate's fault.
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
    # STUB: commit 2 fetches each SUBMITTED/PARSE_ERROR candidate's resume
    # through ResumeStore and calls resume_parser.extract_text.
    assert task.job_id is not None
