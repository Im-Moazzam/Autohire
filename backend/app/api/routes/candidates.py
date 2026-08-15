from fastapi import APIRouter, Depends, Query

from app.api import fixtures
from app.api.deps import get_current_recruiter, get_owned_candidate, get_owned_job
from app.models.job import JobPosting
from app.schemas.candidate import (
    CandidateDetailOut,
    CandidateOut,
    CandidateUpdate,
    RankedCandidateOut,
)
from app.schemas.common import Page, PaginationParams, error_responses, paginate, pagination_params
from app.schemas.enums import SubmissionStatus

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


def _to_candidate_out(candidate: dict) -> CandidateOut:
    return CandidateOut(**candidate, resume_url=fixtures.resume_url_for(candidate))


def _to_ranked_out(candidate: dict) -> RankedCandidateOut:
    return RankedCandidateOut(**candidate, resume_url=fixtures.resume_url_for(candidate))


def _to_detail_out(candidate: dict) -> CandidateDetailOut:
    base = {k: v for k, v in candidate.items() if k != "form_responses"}
    return CandidateDetailOut(
        **base,
        resume_url=fixtures.resume_url_for(candidate),
        form_responses=fixtures.form_responses_for(candidate),
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
) -> Page[CandidateOut]:
    # STUB: US-13 — parse-failed candidates are a filter over this one collection
    # (?submission_status=PARSE_ERROR), never a second list (ADR-004 P2).
    candidates = fixtures.candidates_for_job(job.job_id)
    if submission_status is not None:
        candidates = [c for c in candidates if c["submission_status"] == submission_status]
    if q:
        candidates = [c for c in candidates if q.lower() in c["full_name"].lower()]
    return paginate([_to_candidate_out(c) for c in candidates], params)


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
def get_candidate(candidate: dict = Depends(get_owned_candidate)) -> CandidateDetailOut:
    # STUB: US-13
    return _to_detail_out(candidate)


@candidates_router.patch(
    "/{candidate_id}",
    response_model=CandidateDetailOut,
    responses=error_responses(401, 404, 422),
)
def update_candidate(
    payload: CandidateUpdate, candidate: dict = Depends(get_owned_candidate)
) -> CandidateDetailOut:
    # STUB: US-13
    updated = {**candidate, "submission_status": payload.submission_status}
    return _to_detail_out(updated)
