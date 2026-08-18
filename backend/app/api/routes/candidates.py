from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import fixtures
from app.api.deps import get_current_recruiter, get_db, get_owned_candidate, get_owned_job
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.schemas.candidate import (
    CandidateDetailOut,
    CandidateOut,
    CandidateUpdate,
    RankedCandidateOut,
)
from app.schemas.common import Page, PaginationParams, error_responses, paginate, pagination_params
from app.schemas.enums import SubmissionStatus
from app.services import candidate_service

job_candidates_router = APIRouter(
    prefix="/jobs",
    tags=["candidates"],
    dependencies=[Depends(get_current_recruiter)],
)
candidates_router = APIRouter(
    prefix="/candidates",
    tags=["candidates"],
    dependencies=[Depends(get_current_recruiter)],
)

_RESUME_NOT_FOUND = {
    "code": "RESUME_NOT_FOUND",
    "message": "No resume is stored for this candidate.",
}

_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}


def _to_candidate_out(candidate: Candidate) -> CandidateOut:
    return CandidateOut(
        candidate_id=candidate.candidate_id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone_number=candidate.phone_number,
        submission_status=candidate.submission_status,
        submitted_at=candidate.submitted_at,
        parse_error=candidate.parse_error,
        resume_url=candidate_service.resume_url_for(candidate),
    )


def _to_ranked_out(candidate: dict) -> RankedCandidateOut:
    return RankedCandidateOut(**candidate, resume_url=fixtures.resume_url_for(candidate))


def _to_detail_out(db: Session, candidate: Candidate) -> CandidateDetailOut:
    base = _to_candidate_out(candidate)
    return CandidateDetailOut(
        **base.model_dump(),
        form_responses=candidate_service.form_responses(db, candidate.candidate_id),
    )


@job_candidates_router.get(
    "/{job_id}/candidates",
    response_model=Page[CandidateOut],
    responses=error_responses(401, 404),
)
def list_candidates(
    submission_status: SubmissionStatus | None = Query(default=None),
    q: str | None = Query(default=None),
    job: JobPosting = Depends(get_owned_job),
    params: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> Page[CandidateOut]:
    candidates, total = candidate_service.list_candidates(
        db, job.job_id, params, submission_status, q
    )
    return Page[CandidateOut](
        items=[_to_candidate_out(c) for c in candidates],
        total=total,
        page=params.page,
        size=params.size,
    )


@job_candidates_router.get(
    "/{job_id}/candidates/ranked",
    response_model=Page[RankedCandidateOut],
    responses=error_responses(401, 404),
)
def list_ranked_candidates(
    min_score: float | None = Query(default=None),
    skill: str | None = Query(default=None),
    job: JobPosting = Depends(get_owned_job),
    params: PaginationParams = Depends(pagination_params),
) -> Page[RankedCandidateOut]:
    # STUB: US-19
    candidates = [
        c for c in fixtures.candidates_for_job(job.job_id) if c["rank_position"] is not None
    ]
    if min_score is not None:
        candidates = [c for c in candidates if (c["semantic_score"] or 0) >= min_score]
    if skill:
        candidates = [c for c in candidates if skill in c["matched_skills"]]
    candidates.sort(key=lambda c: c["rank_position"])
    return paginate([_to_ranked_out(c) for c in candidates], params)


@candidates_router.get(
    "/{candidate_id}", response_model=CandidateDetailOut, responses=error_responses(401, 404)
)
def get_candidate(
    candidate: Candidate = Depends(get_owned_candidate), db: Session = Depends(get_db)
) -> CandidateDetailOut:
    return _to_detail_out(db, candidate)


@candidates_router.get(
    "/{candidate_id}/resume",
    response_class=FileResponse,
    responses=error_responses(401, 404),
)
def download_resume(candidate: Candidate = Depends(get_owned_candidate)) -> FileResponse:
    # Local mode only — resume_storage_key is always None in cloud mode
    # (candidate_service.submit_application only sets it when APP_ENV=local),
    # so this 404s there and the frontend uses resume_url's Drive link instead.
    # Never build a redirect to a client-declared storage_key/webViewLink pair:
    # the path is asserted inside the job's folder before it is ever opened,
    # defence in depth on top of the server-generated filename (same as US-12).
    path = candidate_service.resolve_resume_path(candidate)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_RESUME_NOT_FOUND)
    extension = path.suffix.lstrip(".").lower()
    media_type = _MIME_BY_EXT.get(extension, "application/octet-stream")
    # filename is the stored basename (server-generated uuid4 + extension) —
    # never the candidate's original filename, so nothing candidate-supplied
    # reaches a response header. FileResponse defaults to Content-Disposition:
    # attachment, so a malicious PDF can't execute in the recruiter's origin.
    return FileResponse(path=path, media_type=media_type, filename=path.name)


@candidates_router.patch(
    "/{candidate_id}",
    response_model=CandidateDetailOut,
    responses=error_responses(401, 404, 422),
)
def update_candidate(
    payload: CandidateUpdate,
    candidate: Candidate = Depends(get_owned_candidate),
    db: Session = Depends(get_db),
) -> CandidateDetailOut:
    candidate.submission_status = payload.submission_status
    db.commit()
    db.refresh(candidate)
    return _to_detail_out(db, candidate)
