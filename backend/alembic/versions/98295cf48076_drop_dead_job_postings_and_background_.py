"""drop dead job_postings and background_tasks columns

Revision ID: 98295cf48076
Revises: f7a8b9c0d1e2
Create Date: 2026-08-24 08:15:16.972464

TS-06/R-09: three columns confirmed to have zero readers outside their own
model definition/migration. Unconditionally dead, not deferred:
- job_postings.google_form_id / .google_form_url — Forms API rejected
  (ADR-001); apply_slug replaced them entirely (drift row 1/7).
- background_tasks.retry_count — declared, never incremented by any task.
Real downgrade re-adds both, nullable, so this is reversible.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "98295cf48076"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("job_postings", "google_form_id")
    op.drop_column("job_postings", "google_form_url")
    op.drop_column("background_tasks", "retry_count")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("background_tasks", sa.Column("retry_count", sa.Integer(), nullable=True))
    op.add_column("job_postings", sa.Column("google_form_url", sa.Text(), nullable=True))
    op.add_column("job_postings", sa.Column("google_form_id", sa.String(length=255), nullable=True))
