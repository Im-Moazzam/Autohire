import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.adapters.base import ResumeStore
from app.core.config import settings
from app.core.exceptions import JobNotAccepting
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.models.template import FormTemplate
from app.schemas.common import PaginationParams
from app.schemas.enums import JobStatus, SubmissionStatus
from app.schemas.job import JobCreate, JobUpdate
from app.services import template_service

_TEMPLATE_NOT_FOUND = {"code": "TEMPLATE_NOT_FOUND", "message": "Template not found."}
_MAX_SLUG_ATTEMPTS = 5

# Legal transition graph, ADR-004 P3 / docs/api-contract.md § Jobs. Moved out
# of app/api/fixtures.py — jobs.py was its only caller.
_LEGAL_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DRAFT: {JobStatus.LIVE},
    JobStatus.LIVE: {JobStatus.CLOSED},
    JobStatus.CLOSED: {JobStatus.PROCESSED},
    JobStatus.PROCESSED: set(),
}


def is_legal_transition(current: JobStatus, target: JobStatus) -> bool:
    if current == target:
        return True
    return target in _LEGAL_TRANSITIONS[current]


def submission_counts_by_job(db: Session, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """One GROUP BY over the caller's page of job_ids — never the whole table —
    so a list endpoint stays a single bounded query (closes docs/drift.md row 29)."""
    if not job_ids:
        return {}
    rows = db.execute(
        select(Candidate.job_id, func.count())
        .where(Candidate.job_id.in_(job_ids), Candidate.deleted_at.is_(None))
        .group_by(Candidate.job_id)
    ).all()
    return {job_id: count for job_id, count in rows}


def submission_counts_by_status(db: Session, job_id: uuid.UUID) -> dict[SubmissionStatus, int]:
    """Zero-filled across every SubmissionStatus, so the detail response never
    omits a key the frontend expects."""
    counts: dict[SubmissionStatus, int] = dict.fromkeys(SubmissionStatus, 0)
    rows = db.execute(
        select(Candidate.submission_status, func.count())
        .where(Candidate.job_id == job_id, Candidate.deleted_at.is_(None))
        .group_by(Candidate.submission_status)
    ).all()
    for status_, count in rows:
        counts[status_] = count
    return counts


def _new_slug() -> str:
    return secrets.token_urlsafe(12)


def list_jobs(
    db: Session,
    recruiter_id: uuid.UUID,
    params: PaginationParams,
    status_filter: JobStatus | None,
    q: str | None,
) -> tuple[list[JobPosting], int]:
    base = select(JobPosting).where(
        JobPosting.recruiter_id == recruiter_id, JobPosting.deleted_at.is_(None)
    )
    if status_filter is not None:
        base = base.where(JobPosting.status == status_filter)
    if q:
        base = base.where(JobPosting.job_title.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(JobPosting.created_at)
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return list(rows), total


def get_job(db: Session, recruiter_id: uuid.UUID, job_id: uuid.UUID) -> JobPosting | None:
    return db.scalar(
        select(JobPosting).where(
            JobPosting.job_id == job_id,
            JobPosting.recruiter_id == recruiter_id,
            JobPosting.deleted_at.is_(None),
        )
    )


def get_job_by_slug(db: Session, apply_slug: str) -> JobPosting | None:
    """Public lookup — deliberately NOT scoped by recruiter_id. The caller is
    unauthenticated and the slug IS the capability (US-06); there is no
    recruiter identity to scope by. Soft-deleted rows are excluded, so a
    deleted job is indistinguishable from an unknown slug."""
    return db.scalar(
        select(JobPosting)
        .where(JobPosting.apply_slug == apply_slug, JobPosting.deleted_at.is_(None))
        .options(selectinload(JobPosting.template).selectinload(FormTemplate.fields))
    )


def assert_job_accepting(job: JobPosting) -> None:
    """LIVE AND is_accepting_responses AND now < expires_at — all three,
    evaluated per request. US-06 deliberately leaves an expired job LIVE
    (US-08 owns the status transition), so expiry is never inferred from
    status. US-12 calls this before writing a submission; do not inline a
    second copy of this check."""
    if job.status != JobStatus.LIVE:
        raise JobNotAccepting(job.job_title, "CLOSED")
    if datetime.now(UTC) >= job.expires_at:
        raise JobNotAccepting(job.job_title, "EXPIRED")
    if not job.is_accepting_responses:
        raise JobNotAccepting(job.job_title, "PAUSED")


def job_references_template(db: Session, template_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(JobPosting.job_id).where(
                JobPosting.template_id == template_id, JobPosting.deleted_at.is_(None)
            )
        )
        is not None
    )


def _insert_draft(db: Session, recruiter: Recruiter, payload: JobCreate) -> JobPosting:
    for _ in range(_MAX_SLUG_ATTEMPTS):
        job = JobPosting(
            recruiter_id=recruiter.recruiter_id,
            template_id=payload.template_id,
            job_title=payload.job_title,
            job_description=payload.job_description,
            expires_at=payload.expires_at,
            apply_slug=_new_slug(),
            status=JobStatus.DRAFT,
        )
        db.add(job)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(job)
        return job
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "SLUG_GENERATION_FAILED", "message": "Could not generate a unique slug."},
    )


def finalize_launch(
    db: Session, recruiter: Recruiter, job: JobPosting, store: ResumeStore
) -> JobPosting:
    """DRAFT -> LIVE. No DB transaction is held open across the store call —
    the DRAFT row is already committed by the time this runs, so a failure
    here leaves the row exactly where it was, retryable via the same call."""
    if job.google_drive_folder_id is None:
        try:
            folder_id = store.create_job_folder(recruiter, job.job_id, job.job_title)
        except Exception as exc:
            # A Drive failure is an upstream problem (502); a local filesystem
            # error is our own server's problem (500) — not the same failure.
            status_code = (
                status.HTTP_500_INTERNAL_SERVER_ERROR
                if settings.resume_store == "local"
                else status.HTTP_502_BAD_GATEWAY
            )
            raise HTTPException(
                status_code=status_code,
                detail={
                    "code": "RESUME_FOLDER_FAILED",
                    "message": "Could not create the resume storage folder.",
                    "details": {"job_id": str(job.job_id), "cause": str(exc)},
                },
            ) from exc
        job.google_drive_folder_id = folder_id
    job.status = JobStatus.LIVE
    job.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job


def create_job(
    db: Session, recruiter: Recruiter, payload: JobCreate, store: ResumeStore
) -> JobPosting:
    template = template_service.get_template(db, recruiter.recruiter_id, payload.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_TEMPLATE_NOT_FOUND)
    job = _insert_draft(db, recruiter, payload)
    return finalize_launch(db, recruiter, job, store)


def update_job(
    db: Session, recruiter: Recruiter, job: JobPosting, payload: JobUpdate, store: ResumeStore
) -> JobPosting:
    if payload.status is not None and payload.status != job.status:
        if not is_legal_transition(job.status, payload.status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "INVALID_STATE_TRANSITION",
                    "message": f"Cannot transition job from {job.status} to {payload.status}.",
                },
            )
        if job.status == JobStatus.DRAFT and payload.status == JobStatus.LIVE:
            # Retry path: same finalize_launch the create path runs, so a
            # second failed attempt leaves the row DRAFT again, not a new row.
            job = finalize_launch(db, recruiter, job, store)
        else:
            job.status = payload.status
            if payload.status == JobStatus.CLOSED:
                job.is_accepting_responses = False

    if payload.job_title is not None:
        job.job_title = payload.job_title
    if payload.job_description is not None:
        job.job_description = payload.job_description
    if payload.expires_at is not None:
        job.expires_at = payload.expires_at
    if payload.is_accepting_responses is not None:
        job.is_accepting_responses = payload.is_accepting_responses

    job.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return job
