import uuid
from collections.abc import Generator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.recruiter import Recruiter, RecruiterState
from app.models.template import FormTemplate
from app.services import candidate_service, job_service, template_service
from app.services.auth_service import SESSION_COOKIE, read_session_cookie

_NOT_AUTHENTICATED = {"code": "NOT_AUTHENTICATED", "message": "not authenticated"}
_NOT_AUTHORIZED = {"code": "NOT_AUTHORIZED", "message": "not authorized"}


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_recruiter(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> Recruiter:
    raw_id = read_session_cookie(session_cookie)
    if raw_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_NOT_AUTHENTICATED)
    try:
        recruiter_id = uuid.UUID(raw_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_NOT_AUTHENTICATED
        ) from None
    recruiter = db.get(Recruiter, recruiter_id)
    if recruiter is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_NOT_AUTHENTICATED)
    # A suspended recruiter (TS-14 admin revoke) still has a valid session
    # cookie/row — only this check actually locks them out.
    if recruiter.account_state == RecruiterState.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_NOT_AUTHENTICATED)
    return recruiter


def get_current_admin(
    recruiter: Recruiter = Depends(get_current_recruiter),
) -> Recruiter:
    """Single hardcoded admin identity (TS-14) — still requires a real
    Google-authenticated session via get_current_recruiter, just gates which
    authenticated recruiter may reach /admin/*. Blank ADMIN_EMAIL disables
    the admin dashboard entirely, since no recruiter email ever matches ""."""
    if not settings.admin_email or recruiter.email != settings.admin_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_NOT_AUTHORIZED)
    return recruiter


def get_owned_job(
    job_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> JobPosting:
    job = job_service.get_job(db, recruiter.recruiter_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Job not found."},
        )
    return job


def get_owned_candidate(
    candidate_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> Candidate:
    candidate = candidate_service.get_owned_candidate(db, recruiter.recruiter_id, candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CANDIDATE_NOT_FOUND", "message": "Candidate not found."},
        )
    return candidate


def get_owned_template(
    template_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> FormTemplate:
    template = template_service.get_template(db, recruiter.recruiter_id, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TEMPLATE_NOT_FOUND", "message": "Template not found."},
        )
    return template
