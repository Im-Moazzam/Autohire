"""No get_current_recruiter anywhere in this module, deliberately (ADR-004 P1) —
these are the only two unauthenticated endpoints in the system. A test in
tests/test_stub_common.py inspects this router's routes to assert that stays true."""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import FormData

from app.adapters.base import ResumeStore
from app.adapters.resume_store import get_resume_store
from app.api.deps import get_db
from app.core.config import settings
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.schemas.common import error_responses
from app.schemas.enums import JobStatus
from app.schemas.public import ApplySuccessOut, PublicJobOut
from app.services import candidate_service, job_service

router = APIRouter(prefix="/public", tags=["public"])

_JOB_NOT_FOUND = {"code": "JOB_NOT_FOUND", "message": "No job found for that link."}

# Best-effort only: FastAPI has already resolved the `resume: UploadFile`
# parameter (and therefore parsed the full multipart body) by the time a
# route function runs — see the ponytail note in resume_validation.read_capped
# for why that's not worth giving up the declarative UploadFile signature to
# fix. This dependency runs before that parsing and rejects the common case
# (a client that sends an honest, grossly-oversized Content-Length) without
# touching the body at all. A lying header can only make this check miss,
# never falsely reject — read_capped is what actually enforces the cap.
_CONTENT_LENGTH_SLACK_BYTES = 64 * 1024


def _reject_oversized_declared_length(request: Request) -> None:
    declared = request.headers.get("content-length")
    if declared is None:
        return
    try:
        size = int(declared)
    except ValueError:
        return
    if size > settings.max_resume_mb * 1024 * 1024 + _CONTENT_LENGTH_SLACK_BYTES:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Resume exceeds {settings.max_resume_mb}MB.",
            },
        )


def _get_public_job(db: Session, apply_slug: str) -> JobPosting:
    """Unknown slug, soft-deleted, and DRAFT all 404 identically — a draft is
    not "closed", it's unlaunched, and a distinguishable response would leak
    that a posting exists before the recruiter has shared it."""
    job = job_service.get_job_by_slug(db, apply_slug)
    if job is None or job.status == JobStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_JOB_NOT_FOUND)
    return job


@router.get(
    "/apply/{apply_slug}",
    response_model=PublicJobOut,
    responses=error_responses(404, 410),
)
def get_public_job(apply_slug: str, db: Session = Depends(get_db)) -> PublicJobOut:
    job = _get_public_job(db, apply_slug)
    job_service.assert_job_accepting(job)
    return PublicJobOut(
        job_title=job.job_title,
        job_description=job.job_description,
        fields=job.template.fields,
        is_accepting_responses=job.is_accepting_responses,
        expires_at=job.expires_at,
    )


def _process_submission(
    db: Session, apply_slug: str, form: FormData, resume: UploadFile, store: ResumeStore
) -> Candidate:
    job = _get_public_job(db, apply_slug)
    return candidate_service.submit_application(db, job, form, resume, store)


@router.post(
    "/apply/{apply_slug}",
    response_model=ApplySuccessOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 410, 413, 415, 422, 500, 502),
    dependencies=[Depends(_reject_oversized_declared_length)],
)
async def submit_application(
    apply_slug: str,
    request: Request,
    resume: UploadFile,
    db: Session = Depends(get_db),
    store: ResumeStore = Depends(get_resume_store),
) -> ApplySuccessOut:
    # Rate limiting by IP is a documented gap (docs/drift.md), not built here —
    # out of scope per the story.
    #
    # async only so `await request.form()` can read the field_id-keyed parts
    # FastAPI already parsed to resolve `resume: UploadFile` (the cached
    # result, not a second parse) — request.form() has no sync equivalent.
    # Everything blocking (DB, and in cloud mode google_call's sleep-based
    # retry) runs via run_in_threadpool, same as FastAPI does automatically
    # for a sync route — google_call must never run inline on the event loop
    # (app/adapters/google/session.py).
    form = await request.form()
    candidate = await run_in_threadpool(_process_submission, db, apply_slug, form, resume, store)
    return ApplySuccessOut(
        submitted_at=candidate.submitted_at,
        message="Application received.",
    )
