"""create ai_analysis_results

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
Create Date: 2026-08-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_analysis_results",
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("semantic_score", sa.Float(), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("matched_skills", postgresql.JSONB(), nullable=True),
        sa.Column("missing_skills", postgresql.JSONB(), nullable=True),
        sa.Column("ai_feedback_summary", sa.Text(), nullable=True),
        sa.Column("evidence_snippets", postgresql.JSONB(), nullable=True),
        sa.Column("vector_id", sa.String(255), nullable=True),
        # EMBEDDING_DIM read from settings, never a literal (TC-07) — a
        # local/cloud dimension mismatch would silently corrupt the index.
        sa.Column("embedding", Vector(settings.embedding_dim), nullable=True),
        sa.Column(
            "processed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_ai_analysis_results_job_rank",
        "ai_analysis_results",
        ["job_id", "rank_position"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_ai_analysis_results_job_rank", table_name="ai_analysis_results")
    op.drop_table("ai_analysis_results")
