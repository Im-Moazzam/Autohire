"""No get_current_recruiter anywhere in this module, deliberately (ADR-004 P1) —
these are the only two unauthenticated endpoints in the system. A test in
tests/test_stub_public.py inspects this router's routes to assert that stays true."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api import fixtures
from app.schemas.common import error_responses
from app.schemas.public import ApplySuccessOut, PublicJobOut

router = APIRouter(prefix="/public", tags=["public"])


def _job_by_slug(apply_slug: str) -> dict:
    for job in fixtures.JOBS.values():
        if job["apply_slug"] == apply_slug:
            return job
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "JOB_NOT_FOUND", "message": "No job found for that link."},
    )


@router.get(
    "/apply/{apply_slug}",
    response_model=PublicJobOut,
    responses=error_responses(404, 410),
)
def get_public_job(apply_slug: str) -> PublicJobOut:
    # STUB: US-11
    job = _job_by_slug(apply_slug)
    if job["expires_at"] < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "JOB_EXPIRED", "message": "This application link has expired."},
        )
    if job["status"] != "LIVE" or not job["is_accepting_responses"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "JOB_NOT_ACCEPTING",
                "message": "This job is not currently accepting applications.",
            },
        )
    template = fixtures.TEMPLATES[job["template_id"]]
    return PublicJobOut(
        job_title=job["job_title"],
        job_description=job["job_description"],
        fields=template["fields"],
        is_accepting_responses=job["is_accepting_responses"],
        expires_at=job["expires_at"],
    )


@router.post(
    "/apply/{apply_slug}",
    response_model=ApplySuccessOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 410, 413, 415),
)
def submit_application(apply_slug: str, resume: UploadFile) -> ApplySuccessOut:
    # STUB: US-12 — real route validates file type by magic bytes, caps at 5MB,
    # rate-limits by IP, and persists the candidate + form responses. 413/415 are
    # declared above but not enforced yet, so the client is typed for that story.
    job = _job_by_slug(apply_slug)
    if job["expires_at"] < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "JOB_EXPIRED", "message": "This application link has expired."},
        )
    if job["status"] != "LIVE" or not job["is_accepting_responses"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "JOB_NOT_ACCEPTING",
                "message": "This job is not currently accepting applications.",
            },
        )
    return ApplySuccessOut(
        submitted_at=fixtures.NOW,
        message="Application received.",
    )
