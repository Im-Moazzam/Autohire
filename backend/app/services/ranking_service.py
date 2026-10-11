import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.candidate import Candidate
from app.schemas.common import PaginationParams


def list_ranked_candidates(
    db: Session,
    job_id: uuid.UUID,
    params: PaginationParams,
    min_score: float | None,
    skill: str | None,
) -> tuple[list[tuple[Candidate, AiAnalysisResult]], int]:
    """Mirrors candidate_service.list_candidates: a COUNT over the filtered
    subquery, then one bounded page (TC-13) — never N+1 over analysis rows."""
    base = (
        select(Candidate, AiAnalysisResult)
        .join(AiAnalysisResult, AiAnalysisResult.candidate_id == Candidate.candidate_id)
        .where(Candidate.job_id == job_id, Candidate.deleted_at.is_(None))
    )
    if min_score is not None:
        # Filters on the blend, not the cosine half — min_score has to mean the
        # same number the recruiter sees as match_score, or the filter silently
        # disagrees with the column it appears to act on (ADR-006).
        base = base.where(AiAnalysisResult.final_score >= min_score)
    if skill:
        base = base.where(AiAnalysisResult.matched_skills.contains([skill]))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(AiAnalysisResult.rank_position.asc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return [(row[0], row[1]) for row in rows], total


def processed_at_for_job(db: Session, job_id: uuid.UUID) -> datetime | None:
    """Null until BATCH_RANKING has completed once — a job never ranked is a
    200 with an empty shortlist (TC-10), not something to 404 or fake a
    timestamp for."""
    return db.scalar(
        select(func.max(AiAnalysisResult.processed_at)).where(AiAnalysisResult.job_id == job_id)
    )
