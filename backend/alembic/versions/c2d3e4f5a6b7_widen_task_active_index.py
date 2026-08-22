"""widen task active index to cover BATCH_RANKING

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-22 00:00:01.000000

The concurrency guard behind PROCESSING_IN_PROGRESS (uq_background_tasks_job_active)
only covered RESUME_PARSE. US-18 adds BATCH_RANKING as a second task type that must
never overlap a job's active RESUME_PARSE (or another BATCH_RANKING) — widen the
partial unique index's predicate rather than adding a second, parallel index, so
"one active task per job" stays a single rule.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_WHERE = "task_type = 'RESUME_PARSE' AND status IN ('PENDING', 'RUNNING')"
_NEW_WHERE = "task_type IN ('RESUME_PARSE', 'BATCH_RANKING') AND status IN ('PENDING', 'RUNNING')"


def upgrade() -> None:
    """Upgrade schema."""
    # Dropping and recreating a partial unique index fails outright if any
    # existing rows already violate the new, wider predicate (two jobs each
    # with a concurrent RESUME_PARSE and BATCH_RANKING row). That's expected
    # on a fresh clone but not guaranteed on a populated dev/demo database —
    # fail loudly with a clear message instead of alembic's opaque
    # IntegrityError if it happens.
    conflicts = (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            SELECT job_id FROM background_tasks
            WHERE {_NEW_WHERE}
            GROUP BY job_id
            HAVING COUNT(*) > 1
            """
            )
        )
        .fetchall()
    )
    if conflicts:
        job_ids = ", ".join(str(row[0]) for row in conflicts)
        raise RuntimeError(
            "cannot widen uq_background_tasks_job_active: job(s) "
            f"{job_ids} already have more than one PENDING/RUNNING task. "
            "Resolve (cancel/complete) those tasks before upgrading."
        )

    op.drop_index("uq_background_tasks_job_active", table_name="background_tasks")
    op.create_index(
        "uq_background_tasks_job_active",
        "background_tasks",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text(_NEW_WHERE),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_background_tasks_job_active", table_name="background_tasks")
    op.create_index(
        "uq_background_tasks_job_active",
        "background_tasks",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text(_OLD_WHERE),
    )
