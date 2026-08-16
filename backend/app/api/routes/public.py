"""No get_current_recruiter anywhere in this module, deliberately (ADR-004 P1) —
these are the only two unauthenticated endpoints in the system. A test in
tests/test_stub_public.py inspects this router's routes to assert that stays true."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api import fixtures
from app.api.deps import get_db
from app.models.job import JobPosting
from app.schemas.common import error_responses
from app.schemas.enums import JobStatus
from app.schemas.public import ApplySuccessOut, PublicJobOut
from app.services import job_service

router = APIRouter(prefix="/public", tags=["public"])

_JOB_NOT_FOUND = {"code": "JOB_NOT_FOUND", "message": "No job found for that link."}


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


@router.post(
    "/apply/{apply_slug}",
    response_model=ApplySuccessOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 410, 413, 415),
)
def submit_application(
    apply_slug: str, resume: UploadFile, db: Session = Depends(get_db)
) -> ApplySuccessOut:
    # STUB: US-12 — real route validates file type by magic bytes, caps at 5MB,
    # rate-limits by IP, and persists the candidate + form responses. 413/415 are
    # declared above but not enforced yet, so the client is typed for that story.
    job = _get_public_job(db, apply_slug)
    job_service.assert_job_accepting(job)
    return ApplySuccessOut(
        submitted_at=fixtures.NOW,
        message="Application received.",
    )
