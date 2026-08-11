import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import fixtures
from app.api.deps import get_current_recruiter, get_owned_job
from app.core.config import settings
from app.schemas.common import Page, PaginationParams, error_responses, paginate, pagination_params
from app.schemas.enums import JobStatus, SubmissionStatus, TaskStatus
from app.schemas.job import JobCreate, JobDetailOut, JobOut, JobUpdate
from app.schemas.task import ProcessStatusOut, TaskOut

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_recruiter)],
)


def _apply_url(apply_slug: str) -> str:
    # ADR-004 P10: PUBLIC_APPLY_BASE_URL already ends in /apply — don't append it again.
    return f"{settings.public_apply_base_url}/{apply_slug}"


def _submission_counts(job_id: uuid.UUID) -> dict[SubmissionStatus, int]:
    counts = Counter(c["submission_status"] for c in fixtures.candidates_for_job(job_id))
    return {status_: counts.get(status_, 0) for status_ in SubmissionStatus}


def _to_job_out(job: dict) -> JobOut:
    return JobOut(
        **job,
        submission_count=len(fixtures.candidates_for_job(job["job_id"])),
    )


def _to_job_detail_out(job: dict) -> JobDetailOut:
    return JobDetailOut(
        **job,
        submission_count=len(fixtures.candidates_for_job(job["job_id"])),
        apply_url=_apply_url(job["apply_slug"]),
        submission_counts=_submission_counts(job["job_id"]),
    )


@router.get("", response_model=Page[JobOut], responses=error_responses(401))
def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    params: PaginationParams = Depends(pagination_params),
) -> Page[JobOut]:
    # STUB: US-06
    jobs = list(fixtures.JOBS.values())
    if status_filter is not None:
        jobs = [j for j in jobs if j["status"] == status_filter]
    if q:
        jobs = [j for j in jobs if q.lower() in j["job_title"].lower()]
    return paginate([_to_job_out(j) for j in jobs], params)


@router.post(
    "",
    response_model=JobDetailOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(401, 422),
)
def create_job(payload: JobCreate) -> JobDetailOut:
    # STUB: US-06 — real route creates the Drive folder, apply_slug, JD embedding.
    template = fixtures.TEMPLATES.get(payload.template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TEMPLATE_NOT_FOUND", "message": "Template not found."},
        )
    job = {
        "job_id": uuid.uuid4(),
        "job_title": payload.job_title,
        "job_description": payload.job_description,
        "template_id": payload.template_id,
        "status": JobStatus.LIVE,
        "is_accepting_responses": True,
        "expires_at": payload.expires_at,
        "apply_slug": uuid.uuid4().hex[:16],
        "google_drive_folder_id": None,
        "created_at": fixtures.NOW,
        "updated_at": fixtures.NOW,
    }
    return _to_job_detail_out(job)


@router.get("/{job_id}", response_model=JobDetailOut, responses=error_responses(401, 404))
def get_job(job: dict = Depends(get_owned_job)) -> JobDetailOut:
    # STUB: US-06
    return _to_job_detail_out(job)


@router.patch(
    "/{job_id}", response_model=JobDetailOut, responses=error_responses(401, 404, 409, 422)
)
def update_job(payload: JobUpdate, job: dict = Depends(get_owned_job)) -> JobDetailOut:
    # STUB: US-06/US-09 — closing a job is PATCH {"status": "CLOSED"}, no /close endpoint (ADR-004 P3).
    updated = dict(job)
    if payload.status is not None and payload.status != job["status"]:
        if not fixtures.is_legal_job_transition(job["status"], payload.status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "INVALID_STATE_TRANSITION",
                    "message": f"Cannot transition job from {job['status']} to {payload.status}.",
                },
            )
        updated["status"] = payload.status
    if payload.job_title is not None:
        updated["job_title"] = payload.job_title
    if payload.job_description is not None:
        updated["job_description"] = payload.job_description
    if payload.expires_at is not None:
        updated["expires_at"] = payload.expires_at
    if payload.is_accepting_responses is not None:
        updated["is_accepting_responses"] = payload.is_accepting_responses
    updated["updated_at"] = fixtures.NOW
    return _to_job_detail_out(updated)


@router.post(
    "/{job_id}/process",
    response_model=TaskOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(401, 404, 409),
)
def trigger_process(job: dict = Depends(get_owned_job)) -> TaskOut:
    # STUB: US-15/US-16 — 409 unless CLOSED with candidates.
    candidates = fixtures.candidates_for_job(job["job_id"])
    if job["status"] != JobStatus.CLOSED or not candidates:
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
def process_status(job: dict = Depends(get_owned_job)) -> ProcessStatusOut:
    # STUB: US-15/US-16 — total/processed/failed computed over candidates.submission_status.
    status_data = fixtures.PROCESS_STATUS_BY_JOB.get(
        job["job_id"],
        {
            "status": TaskStatus.PENDING,
            "total": 0,
            "processed": 0,
            "failed": 0,
            "error_message": None,
        },
    )
    return ProcessStatusOut(**status_data)
