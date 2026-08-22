"""BATCH_RANKING — one task per job, same shape as resume_parse_job
(docs/architecture.md, docs/drift.md row 39): own SessionLocal(), acks_late,
scoped autoretry_for, terminal-state no-op for idempotent re-delivery.

Only PARSED and RANKED candidates are ever selected — PARSE_ERROR and
SUBMITTED are skipped, never scored zero (the story's headline AC). RANKED is
included so a re-run (TC-03) has rows to rescore once nothing is PARSED
anymore.

The score is cosine similarity, computed by VectorStore, and nothing else —
ResumeAnalysis (the LLM adapter's return type) has no score field, so an LLM
number has nowhere to become semantic_score.
"""

import hashlib
import uuid
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

_RETRYABLE = (OperationalError,)
_RANKABLE_STATUSES = (SubmissionStatus.PARSED, SubmissionStatus.RANKED)


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
    scored = [
        (candidate, vector, vector_store.cosine_similarity(jd_vector, vector))
        for candidate, vector in zip(candidates, resume_vectors, strict=True)
    ]

    # Deterministic across re-runs (TC-04): score DESC, then submitted_at ASC,
    # then candidate_id as a final tiebreaker for genuinely identical rows.
    scored.sort(key=lambda item: (-item[2], item[0].submitted_at, str(item[0].candidate_id)))

    vector_id = f"{settings.embedding_model}:{settings.embedding_dim}"
    processed_at = datetime.now(UTC)
    for rank_position, (candidate, vector, score) in enumerate(scored, start=1):
        try:
            analysis: ResumeAnalysis | None = analyzer.analyze(
                job.job_description, candidate.resume_text or ""
            )
        except Exception:
            # A failed LLM pass degrades to NULL skills/feedback and does not
            # fail the candidate — the score is already computed and is the
            # ranking (TC-05).
            analysis = None

        _upsert_analysis(
            db,
            candidate,
            job.job_id,
            score,
            rank_position,
            vector,
            vector_id,
            processed_at,
            analysis,
        )
        candidate.submission_status = SubmissionStatus.RANKED

    job.status = JobStatus.PROCESSED
    db.commit()


def _upsert_analysis(
    db: Session,
    candidate: Candidate,
    job_id: uuid.UUID,
    score: float,
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
        "semantic_score": score,
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
