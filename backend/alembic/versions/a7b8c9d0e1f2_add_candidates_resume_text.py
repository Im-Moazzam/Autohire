"""add candidates.resume_text

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-18 00:00:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # docs/drift.md: ai_analysis_results (schema.md's designated home) doesn't
    # exist until US-18, so extracted text lives here until that table lands.
    op.add_column("candidates", sa.Column("resume_text", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("candidates", "resume_text")
