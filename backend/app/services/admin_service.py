import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.models.recruiter import Recruiter, RecruiterState
from app.schemas.common import PaginationParams
from app.schemas.enums import TaskStatus, TaskType


def list_recruiters(
    db: Session, params: PaginationParams
) -> tuple[list[tuple[Recruiter, int, int, int, int]], int]:
    """One row per recruiter, usage totals via correlated scalar subqueries —
    a single bounded query (page size caps at 100, PaginationParams), not an
    N+1 loop. Same per-metric shape as dashboard_service.get_dashboard_stats,
    just evaluated per-recruiter instead of filtered to one."""
    total = db.scalar(select(func.count()).select_from(Recruiter)) or 0

    jobs_count = (
        select(func.count())
        .select_from(JobPosting)
        .where(
            JobPosting.recruiter_id == Recruiter.recruiter_id,
            JobPosting.deleted_at.is_(None),
        )
        .correlate(Recruiter)
        .scalar_subquery()
    )
    candidates_count = (
        select(func.count())
        .select_from(Candidate)
        .join(JobPosting, JobPosting.job_id == Candidate.job_id)
        .where(
            JobPosting.recruiter_id == Recruiter.recruiter_id,
            JobPosting.deleted_at.is_(None),
            Candidate.deleted_at.is_(None),
        )
        .correlate(Recruiter)
        .scalar_subquery()
    )
    interviews_count = (
        select(func.count())
        .select_from(InterviewSlot)
        .where(InterviewSlot.recruiter_id == Recruiter.recruiter_id)
        .correlate(Recruiter)
        .scalar_subquery()
    )
    emails_count = (
        select(func.count())
        .select_from(EmailLog)
        .where(EmailLog.recruiter_id == Recruiter.recruiter_id)
        .correlate(Recruiter)
        .scalar_subquery()
    )

    rows = db.execute(
        select(
            Recruiter,
            jobs_count.label("total_jobs"),
            candidates_count.label("total_candidates"),
            interviews_count.label("total_interviews"),
            emails_count.label("total_emails"),
        )
        .order_by(Recruiter.created_at.desc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows], total


def list_tasks(
    db: Session,
    params: PaginationParams,
    status: TaskStatus | None,
    task_type: TaskType | None,
) -> tuple[list[tuple[BackgroundTask, str]], int]:
    base = select(BackgroundTask, Recruiter.email).join(
        Recruiter, Recruiter.recruiter_id == BackgroundTask.recruiter_id
    )
    if status is not None:
        base = base.where(BackgroundTask.status == status)
    if task_type is not None:
        base = base.where(BackgroundTask.task_type == task_type)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(BackgroundTask.started_at.desc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return [(r[0], r[1]) for r in rows], total


def suspend_recruiter(db: Session, recruiter_id: uuid.UUID) -> Recruiter | None:
    recruiter = db.get(Recruiter, recruiter_id)
    if recruiter is None:
        return None
    recruiter.account_state = RecruiterState.SUSPENDED
    db.commit()
    db.refresh(recruiter)
    return recruiter


def reactivate_recruiter(db: Session, recruiter_id: uuid.UUID) -> Recruiter | None:
    recruiter = db.get(Recruiter, recruiter_id)
    if recruiter is None:
        return None
    recruiter.account_state = RecruiterState.ACTIVE
    db.commit()
    db.refresh(recruiter)
    return recruiter
