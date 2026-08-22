import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.enums import JobStatus, SubmissionStatus, TaskStatus, TaskType
from app.tasks.batch_ranking import batch_ranking_job
from app.tasks.resume_parse import resume_parse_job

_PROCESSING_IN_PROGRESS = {
    "code": "PROCESSING_IN_PROGRESS",
    "message": "A processing task for this job is already running.",
}
_NO_CANDIDATES = {
    "code": "NO_CANDIDATES",
    "message": "This job has no candidates to process.",
}
_INVALID_STATE = {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Job must be CLOSED with candidates to process.",
}
_NO_PARSED_CANDIDATES = {
    "code": "NO_PARSED_CANDIDATES",
    "message": "This job has no PARSED candidates to rank.",
}
_RANK_INVALID_STATE = {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Job must be CLOSED or PROCESSED to rank.",
}

# Statuses "processed" past a successful parse — used by process_status_for_job.
_PROCESSED_STATUSES = {
    SubmissionStatus.PARSED,
    SubmissionStatus.RANKED,
    SubmissionStatus.INVITED,
    SubmissionStatus.CONFIRMED,
    SubmissionStatus.DECLINED,
    SubmissionStatus.RESCHEDULED,
    SubmissionStatus.REJECTED,
}


_ACTIVE_TASK_TYPES = (TaskType.RESUME_PARSE, TaskType.BATCH_RANKING)


def active_task_for_job(db: Session, job_id: uuid.UUID) -> BackgroundTask | None:
    """Any PENDING/RUNNING RESUME_PARSE or BATCH_RANKING task for this job —
    mirrors uq_background_tasks_job_active's widened predicate (US-18), so a
    rank can't start mid-parse and vice versa."""
    return db.scalar(
        select(BackgroundTask).where(
            BackgroundTask.job_id == job_id,
            BackgroundTask.task_type.in_(_ACTIVE_TASK_TYPES),
            BackgroundTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING]),
        )
    )


def enqueue_resume_parse(db: Session, recruiter: Recruiter, job: JobPosting) -> BackgroundTask:
    """Fast-path pre-check, then the real guard: a partial unique index on
    background_tasks (job_id WHERE task_type='RESUME_PARSE' AND status IN
    (PENDING, RUNNING)). Two concurrent POSTs can both pass the pre-check —
    only the index stops both from enqueuing. The row is committed BEFORE
    .delay() is called, so a trace exists even if the broker is unreachable."""
    if active_task_for_job(db, job.job_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PROCESSING_IN_PROGRESS)

    if job.status != JobStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_INVALID_STATE)

    has_candidates = (
        db.scalar(
            select(Candidate.candidate_id).where(
                Candidate.job_id == job.job_id, Candidate.deleted_at.is_(None)
            )
        )
        is not None
    )
    if not has_candidates:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NO_CANDIDATES)

    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id,
        job_id=job.job_id,
        task_type=TaskType.RESUME_PARSE,
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

    async_result = resume_parse_job.delay(str(task.task_id))
    task.celery_task_id = async_result.id
    db.commit()
    db.refresh(task)
    return task


_RANKABLE_STATUSES = (SubmissionStatus.PARSED, SubmissionStatus.RANKED)


def enqueue_batch_ranking(db: Session, recruiter: Recruiter, job: JobPosting) -> BackgroundTask:
    """Mirrors enqueue_resume_parse exactly (ADR-004 P4, same shape as
    POST /process): pre-check, commit PENDING row, .delay(), IntegrityError
    backstop. A separate route rather than chaining off resume_parse_job so a
    recruiter can re-rank without re-parsing, and so TC-06/TC-08's 409s have
    somewhere to be returned from."""
    if active_task_for_job(db, job.job_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_PROCESSING_IN_PROGRESS)

    if job.status not in (JobStatus.CLOSED, JobStatus.PROCESSED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_RANK_INVALID_STATE)

    has_rankable = (
        db.scalar(
            select(Candidate.candidate_id).where(
                Candidate.job_id == job.job_id,
                Candidate.deleted_at.is_(None),
                Candidate.submission_status.in_(_RANKABLE_STATUSES),
            )
        )
        is not None
    )
    if not has_rankable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NO_PARSED_CANDIDATES)

    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id,
        job_id=job.job_id,
        task_type=TaskType.BATCH_RANKING,
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

    async_result = batch_ranking_job.delay(str(task.task_id))
    task.celery_task_id = async_result.id
    db.commit()
    db.refresh(task)
    return task


def process_status_for_job(db: Session, job_id: uuid.UUID) -> dict:
    """total/processed/failed computed from candidate rows, not task state
    (AC, TC-10) — task state only supplies status/error_message."""
    counts: dict[SubmissionStatus, int] = dict.fromkeys(SubmissionStatus, 0)
    rows = db.execute(
        select(Candidate.submission_status, func.count())
        .where(Candidate.job_id == job_id, Candidate.deleted_at.is_(None))
        .group_by(Candidate.submission_status)
    ).all()
    for status_, count in rows:
        counts[status_] = count

    total = sum(counts.values())
    failed = counts[SubmissionStatus.PARSE_ERROR]
    processed = sum(counts[s] for s in _PROCESSED_STATUSES)

    latest_task = db.scalar(
        select(BackgroundTask)
        .where(BackgroundTask.job_id == job_id, BackgroundTask.task_type == TaskType.RESUME_PARSE)
        .order_by(BackgroundTask.started_at.desc())
        .limit(1)
    )
    task_status = latest_task.status if latest_task else TaskStatus.PENDING
    error_message = latest_task.error_message if latest_task else None

    return {
        "status": task_status,
        "total": total,
        "processed": processed,
        "failed": failed,
        "error_message": error_message,
    }
