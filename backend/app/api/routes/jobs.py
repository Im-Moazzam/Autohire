from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.adapters.base import ResumeStore
from app.adapters.resume_store import get_resume_store
from app.api import fixtures
from app.api.deps import get_current_recruiter, get_db, get_owned_job
from app.core.config import settings
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.common import Page, PaginationParams, error_responses, pagination_params
from app.schemas.enums import JobStatus, SubmissionStatus, TaskStatus
from app.schemas.job import JobCreate, JobDetailOut, JobOut, JobUpdate
from app.schemas.task import ProcessStatusOut, TaskOut
from app.services import job_service

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_recruiter)],
)


def _apply_url(apply_slug: str) -> str:
    # ADR-004 P10: PUBLIC_APPLY_BASE_URL already ends in /apply — don't append it again.
    return f"{settings.public_apply_base_url}/{apply_slug}"


def _to_job_out(job: JobPosting, submission_count: int) -> JobOut:
    return JobOut(
        job_id=job.job_id,
        job_title=job.job_title,
        status=job.status,
        is_accepting_responses=job.is_accepting_responses,
        expires_at=job.expires_at,
        submission_count=submission_count,
        created_at=job.created_at,
    )


def _to_job_detail_out(
    job: JobPosting, submission_counts: dict[SubmissionStatus, int]
) -> JobDetailOut:
    return JobDetailOut(
        job_id=job.job_id,
        job_title=job.job_title,
        status=job.status,
        is_accepting_responses=job.is_accepting_responses,
        expires_at=job.expires_at,
        submission_count=sum(submission_counts.values()),
        created_at=job.created_at,
        job_description=job.job_description,
        template_id=job.template_id,
        apply_slug=job.apply_slug,
        apply_url=_apply_url(job.apply_slug),
        google_drive_folder_id=job.google_drive_folder_id,
        updated_at=job.updated_at,
        submission_counts=submission_counts,
    )


@router.get("", response_model=Page[JobOut], responses=error_responses(401))
def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    params: PaginationParams = Depends(pagination_params),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> Page[JobOut]:
    jobs, total = job_service.list_jobs(db, recruiter.recruiter_id, params, status_filter, q)
    counts = job_service.submission_counts_by_job(db, [job.job_id for job in jobs])
    return Page[JobOut](
        items=[_to_job_out(job, counts.get(job.job_id, 0)) for job in jobs],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "",
    response_model=JobDetailOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(401, 404, 422, 502),
)
def create_job(
    payload: JobCreate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
    store: ResumeStore = Depends(get_resume_store),
) -> JobDetailOut:
    job = job_service.create_job(db, recruiter, payload, store)
    return _to_job_detail_out(job, job_service.submission_counts_by_status(db, job.job_id))


@router.get("/{job_id}", response_model=JobDetailOut, responses=error_responses(401, 404))
def get_job(
    job: JobPosting = Depends(get_owned_job), db: Session = Depends(get_db)
) -> JobDetailOut:
    return _to_job_detail_out(job, job_service.submission_counts_by_status(db, job.job_id))


@router.patch(
    "/{job_id}", response_model=JobDetailOut, responses=error_responses(401, 404, 409, 422, 502)
)
def update_job(
    payload: JobUpdate,
    job: JobPosting = Depends(get_owned_job),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
    store: ResumeStore = Depends(get_resume_store),
) -> JobDetailOut:
    # Closing a job is PATCH {"status": "CLOSED"}, no /close endpoint (ADR-004 P3).
    # Retrying a failed launch is PATCH {"status": "LIVE"} on a DRAFT job.
    updated = job_service.update_job(db, recruiter, job, payload, store)
    return _to_job_detail_out(updated, job_service.submission_counts_by_status(db, updated.job_id))


@router.post(
    "/{job_id}/process",
    response_model=TaskOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(401, 404, 409),
)
def trigger_process(job: JobPosting = Depends(get_owned_job)) -> TaskOut:
    # STUB: US-15/US-16 — 409 unless CLOSED with candidates.
    candidates = fixtures.candidates_for_job(job.job_id)
    if job.status != JobStatus.CLOSED or not candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": "Job must be CLOSED with candidates to process.",
            },
        )
    return TaskOut(**fixtures.TASKS[fixtures.TASK_RUNNING_ID])


@router.get(
    "/{job_id}/process/status",
    response_model=ProcessStatusOut,
    responses=error_responses(401, 404),
)
def process_status(job: JobPosting = Depends(get_owned_job)) -> ProcessStatusOut:
    # STUB: US-15/US-16 — total/processed/failed computed over candidates.submission_status.
    status_data = fixtures.PROCESS_STATUS_BY_JOB.get(
        job.job_id,
        {
            "status": TaskStatus.PENDING,
            "total": 0,
            "processed": 0,
            "failed": 0,
            "error_message": None,
        },
    )
    return ProcessStatusOut(**status_data)
