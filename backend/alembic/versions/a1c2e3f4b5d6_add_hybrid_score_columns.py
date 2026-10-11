"""add hybrid score columns to ai_analysis_results

Revision ID: a1c2e3f4b5d6
Revises: 98295cf48076
Create Date: 2026-10-10 16:30:00.000000

ADR-006 makes ranking hybrid: the final order blends the existing cosine
similarity with an LLM relevance judgement. Two additive columns rather than
repurposing semantic_score, whose "pure cosine" meaning is documented in three
places and is what makes the embedding half independently defensible.

- llm_score  — the model's half, normalised 0-1. NULL in local mode, or when the
               analyzer failed; final_score then falls back to cosine alone so a
               provider outage never penalises a candidate (US-18 TC-05).
- final_score — the blend, what rank_position orders by and what the API
               serialises as match_score.

Backfilled from semantic_score so existing ranked rows keep their exact current
ordering: before this migration every score *was* pure cosine, so
final_score = semantic_score is the correct historical value, not a placeholder.
That is also why final_score can be NOT NULL without a two-step.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c2e3f4b5d6"
down_revision: str | Sequence[str] | None = "98295cf48076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("ai_analysis_results", sa.Column("llm_score", sa.Float(), nullable=True))
    # Added nullable, backfilled, then constrained — the only ordering that works
    # on a table that already has rows.
    op.add_column("ai_analysis_results", sa.Column("final_score", sa.Float(), nullable=True))
    op.execute("UPDATE ai_analysis_results SET final_score = semantic_score")
    op.alter_column("ai_analysis_results", "final_score", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Reversible without loss: semantic_score was never modified, so dropping
    # these returns the table to pure-cosine ranking exactly as US-18 left it.
    op.drop_column("ai_analysis_results", "final_score")
    op.drop_column("ai_analysis_results", "llm_score")
