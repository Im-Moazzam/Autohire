"""create background_tasks

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

task_type_enum = sa.Enum(
    "RESUME_PARSE",
    "BATCH_RANKING",
    "EMAIL_DISPATCH",
    "CALENDAR_SYNC",
    "JD_EMBEDDING",
    name="task_type_enum",
)
task_status_enum = sa.Enum(
    "PENDING",
    "RUNNING",
    "SUCCESS",
    "FAILED",
    "RETRIED",
    name="task_status_enum",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "background_tasks",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "recruiter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.job_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("task_type", task_type_enum, nullable=False),
        sa.Column("status", task_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # Query aid for the status endpoint's "newest task for this job" lookup.
    op.create_index("ix_background_tasks_job_active", "background_tasks", ["job_id", "status"])
    # The actual concurrency guard behind the enqueue pre-check: at most one
    # PENDING/RUNNING RESUME_PARSE task per job. A race between two concurrent
    # POST /process calls fails on this index, not on the (read-then-insert)
    # pre-check, same pattern as US-12's uq_candidates_job_email backstop.
    op.create_index(
        "uq_background_tasks_job_active",
        "background_tasks",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("task_type = 'RESUME_PARSE' AND status IN ('PENDING', 'RUNNING')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_background_tasks_job_active", table_name="background_tasks")
    op.drop_index("ix_background_tasks_job_active", table_name="background_tasks")
    op.drop_table("background_tasks")
    task_status_enum.drop(op.get_bind(), checkfirst=True)
    task_type_enum.drop(op.get_bind(), checkfirst=True)
