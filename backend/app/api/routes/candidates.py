from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db, get_owned_candidate, get_owned_job
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.schemas.candidate import (
    CandidateDetailOut,
    CandidateOut,
    CandidateUpdate,
    RankedCandidateOut,
)
from app.schemas.common import Page, PaginationParams, error_responses, pagination_params
from app.schemas.enums import SubmissionStatus
from app.services import candidate_service, ranking_service

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


def _to_ranked_out(candidate: Candidate, analysis: AiAnalysisResult) -> RankedCandidateOut:
    base = _to_candidate_out(candidate)
    return RankedCandidateOut(
        **base.model_dump(),
        rank_position=analysis.rank_position,
        semantic_score=analysis.semantic_score,
        matched_skills=analysis.matched_skills or [],
        missing_skills=analysis.missing_skills or [],
        ai_feedback_summary=analysis.ai_feedback_summary,
    )


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
    db: Session = Depends(get_db),
) -> Page[RankedCandidateOut]:
    rows, total = ranking_service.list_ranked_candidates(db, job.job_id, params, min_score, skill)
    return Page[RankedCandidateOut](
        items=[_to_ranked_out(candidate, analysis) for candidate, analysis in rows],
        total=total,
        page=params.page,
        size=params.size,
    )


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
    responses=error_responses(401, 404, 409, 422),
)
def update_candidate(
    payload: CandidateUpdate,
    candidate: Candidate = Depends(get_owned_candidate),
    db: Session = Depends(get_db),
) -> CandidateDetailOut:
    if not candidate_service.is_legal_transition(
        candidate.submission_status, payload.submission_status
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": (
                    f"Cannot transition candidate from {candidate.submission_status} "
                    f"to {payload.submission_status}."
                ),
            },
        )
    candidate.submission_status = payload.submission_status
    db.commit()
    db.refresh(candidate)
    return _to_detail_out(db, candidate)
