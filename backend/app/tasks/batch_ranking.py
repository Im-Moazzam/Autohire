"""BATCH_RANKING — one task per job, same shape as resume_parse_job
(docs/architecture.md, docs/drift.md row 39): own SessionLocal(), acks_late,
scoped autoretry_for, terminal-state no-op for idempotent re-delivery.

Only PARSED and RANKED candidates are ever selected — PARSE_ERROR and
SUBMITTED are skipped, never scored zero (the story's headline AC). RANKED is
included so a re-run (TC-03) has rows to rescore once nothing is PARSED
anymore.

Ranking is hybrid (ADR-006), superseding US-18's cosine-only rule. Three scores
are written per candidate and only the last is exposed:

    semantic_score — pure cosine similarity from VectorStore. Unchanged.
    llm_score      — the analyzer's relevance judgement, 0-1. NULL in local mode.
    final_score    — (1-w)*semantic + w*llm, ordered by, served as match_score.

The weight lives in config, never in an adapter: an analyzer reports a judgement,
it does not get to decide how much that judgement counts. With llm_score NULL,
final_score is semantic_score alone — so a provider outage degrades to US-18's
exact behaviour rather than penalising the candidate (TC-05).
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from celery import Task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.adapters.analyzer import get_analyzer
from app.adapters.base import ResumeAnalysis
from app.adapters.embedder import get_embedder
from app.adapters.vector_store import get_vector_store
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.schemas.enums import JobStatus, SubmissionStatus, TaskStatus
from app.worker import celery_app

logger = logging.getLogger(__name__)

_RETRYABLE = (OperationalError,)
_RANKABLE_STATUSES = (SubmissionStatus.PARSED, SubmissionStatus.RANKED)


@dataclass(frozen=True)
class _ScoredCandidate:
    """Both score halves plus the analysis, held together so the sort can order
    on final_score while the upsert still has everything it needs to write."""

    candidate: Candidate
    vector: list[float]
    semantic_score: float
    llm_score: float | None
    final_score: float
    analysis: ResumeAnalysis | None


def _blend(semantic_score: float, relevance_score: int | None) -> tuple[float | None, float]:
    """(llm_score, final_score) per ADR-006.

    relevance_score is 0-100 from the adapter; llm_score is stored 0-1 so both
    halves of the blend are on the same scale as semantic_score. A None
    relevance_score (local mode, or a failed analyzer) yields cosine alone —
    never a zero, which would read as "the model judged this candidate
    irrelevant" when in fact it never ran.
    """
    if relevance_score is None:
        return None, semantic_score
    llm_score = relevance_score / 100.0
    weight = settings.llm_score_weight
    return llm_score, (1.0 - weight) * semantic_score + weight * llm_score


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=3,
    soft_time_limit=300,
    retry_backoff=True,
    autoretry_for=_RETRYABLE,
)
def batch_ranking_job(self: Task, task_id: str) -> None:
    with SessionLocal() as db:
        task = db.get(BackgroundTask, uuid.UUID(task_id))
        if task is None:
            return
        if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
            return

        task.status = TaskStatus.RUNNING
        db.commit()

        try:
            _run_batch_ranking(db, task)
        except (SoftTimeLimitExceeded, Retry):
            raise
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.completed_at = datetime.now(UTC)
            db.commit()
            raise

        task.status = TaskStatus.SUCCESS
        task.completed_at = datetime.now(UTC)
        db.commit()


def _jd_provenance_ref(jd_text: str) -> str:
    digest = hashlib.sha256(jd_text.encode()).hexdigest()[:16]
    return f"{settings.embedding_model}:{settings.embedding_dim}:{digest}"


def _run_batch_ranking(db: Session, task: BackgroundTask) -> None:
    assert task.job_id is not None
    job = db.get(JobPosting, task.job_id)
    assert job is not None

    embedder = get_embedder()
    vector_store = get_vector_store()
    analyzer = get_analyzer()

    jd_vector = embedder.embed([job.job_description])[0]
    job.jd_embedding_id = _jd_provenance_ref(job.job_description)
    db.commit()

    candidates = db.scalars(
        select(Candidate).where(
            Candidate.job_id == job.job_id,
            Candidate.deleted_at.is_(None),
            Candidate.submission_status.in_(_RANKABLE_STATUSES),
        )
    ).all()

    if not candidates:
        job.status = JobStatus.PROCESSED
        db.commit()
        return

    # One batched embed() call for every resume, not one call per candidate.
    resume_vectors = embedder.embed([c.resume_text or "" for c in candidates])

    # Analysis has to finish before ranking, not during it: under ADR-006 the
    # sort key depends on llm_score, so every candidate must be scored on both
    # halves before any rank_position can be assigned.
    # ponytail: serial call per candidate — matches the demo scale this runs at
    # (2-3 resumes) and free-tier rate limits. Parallelise only if a run ever
    # outgrows that.
    scored: list[_ScoredCandidate] = []
    for candidate, vector in zip(candidates, resume_vectors, strict=True):
        semantic_score = vector_store.cosine_similarity(jd_vector, vector)
        try:
            analysis: ResumeAnalysis | None = analyzer.analyze(
                job.job_description, candidate.resume_text or ""
            )
        except Exception:
            # A failed analyzer degrades to NULL skills/feedback and cosine-only
            # scoring; it never fails the candidate (TC-05). Logged rather than
            # swallowed — at free-tier rate limits a silent 429 is otherwise
            # indistinguishable from a model that had nothing to say.
            logger.exception(
                "analyzer failed for candidate %s; falling back to cosine-only score",
                candidate.candidate_id,
            )
            analysis = None

        llm_score, final_score = _blend(
            semantic_score, analysis.relevance_score if analysis else None
        )
        scored.append(
            _ScoredCandidate(candidate, vector, semantic_score, llm_score, final_score, analysis)
        )

    # Ordered by the blend, then submitted_at ASC, then candidate_id as a final
    # tiebreaker for genuinely identical rows. The tiebreak chain is unchanged
    # from US-18; what it breaks ties on is now final_score. Re-runs no longer
    # guarantee an identical order — ADR-006 accepts that, and a deterministic
    # analyzer (local mode) still produces one.
    scored.sort(
        key=lambda item: (
            -item.final_score,
            item.candidate.submitted_at,
            str(item.candidate.candidate_id),
        )
    )

    vector_id = f"{settings.embedding_model}:{settings.embedding_dim}"
    processed_at = datetime.now(UTC)
    for rank_position, item in enumerate(scored, start=1):
        _upsert_analysis(
            db,
            item.candidate,
            job.job_id,
            item.semantic_score,
            item.llm_score,
            item.final_score,
            rank_position,
            item.vector,
            vector_id,
            processed_at,
            item.analysis,
        )
        item.candidate.submission_status = SubmissionStatus.RANKED

    job.status = JobStatus.PROCESSED
    db.commit()


def _upsert_analysis(
    db: Session,
    candidate: Candidate,
    job_id: uuid.UUID,
    semantic_score: float,
    llm_score: float | None,
    final_score: float,
    rank_position: int,
    vector: list[float],
    vector_id: str,
    processed_at: datetime,
    analysis: ResumeAnalysis | None,
) -> None:
    """UNIQUE on candidate_id forces this to be an upsert — a re-run (TC-03)
    replaces the prior row instead of accumulating a duplicate."""
    values = {
        "candidate_id": candidate.candidate_id,
        "job_id": job_id,
        "semantic_score": semantic_score,
        "llm_score": llm_score,
        "final_score": final_score,
        "rank_position": rank_position,
        "matched_skills": analysis.matched_skills if analysis else None,
        "missing_skills": analysis.missing_skills if analysis else None,
        "ai_feedback_summary": analysis.feedback if analysis else None,
        "evidence_snippets": analysis.evidence_snippets if analysis else None,
        "vector_id": vector_id,
        "embedding": vector,
        "processed_at": processed_at,
    }
    stmt = pg_insert(AiAnalysisResult).values(**values)
    update_cols = {k: v for k, v in values.items() if k != "candidate_id"}
    stmt = stmt.on_conflict_do_update(index_elements=["candidate_id"], set_=update_cols)
    db.execute(stmt)
