import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.db import Base


class AiAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Denormalized, intentional (docs/schema.md) — lets the ranking query
    # filter by job without a join back through candidates.
    job_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("job_postings.job_id", ondelete="CASCADE"), nullable=False
    )
    # Three scores, one exposed (ADR-006). semantic_score keeps US-18's exact
    # meaning — pure cosine similarity — so it is never repurposed; llm_score is
    # the model's half, NULL in local mode or when the analyzer failed; and
    # final_score is the blend that rank_position orders by and that the API
    # serialises as match_score. The split is stored so a ranking can be
    # explained after the fact, and withheld from the API so the recruiter sees
    # one number.
    semantic_score: Mapped[float] = mapped_column(Float(), nullable=False)
    llm_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    final_score: Mapped[float] = mapped_column(Float(), nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer(), nullable=False)
    matched_skills: Mapped[list[str] | None] = mapped_column(JSONB(), nullable=True)
    missing_skills: Mapped[list[str] | None] = mapped_column(JSONB(), nullable=True)
    ai_feedback_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    evidence_snippets: Mapped[list[str] | None] = mapped_column(JSONB(), nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )
    processed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
