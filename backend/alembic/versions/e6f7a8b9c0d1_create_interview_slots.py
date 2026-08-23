"""create interview_slots

Revision ID: e6f7a8b9c0d1
Revises: d3e4f5a6b7c8
Create Date: 2026-08-23 12:00:00.000000

US-26. Multiple rows per candidate model reschedule history; only one may be
"live" at a time — enforced by a partial UNIQUE on candidate_id WHERE status
IN ('PENDING','CONFIRMED') rather than a plain index, since history must be
retained.

The baseline (docs/schema.md) specifies a plain INDEX on
(recruiter_id, scheduled_at) for conflict checks. The story's AC requires
double-booking to be enforced "with the index plus a conflict check, not
hope" — a plain index enforces nothing on its own, so this is a partial
UNIQUE instead (docs/drift.md). It only catches two live slots at the exact
same instant; the actual overlap check (different slot durations across
generation runs) is an application-level interval check in
interview_service.generate_slots, not something an index alone can express.

intent_detected/candidate_reply_text/reschedule_reason are Phase 2 columns
per the story's "Out of scope" section. candidate_reply_text and
reschedule_reason are included (plain TEXT, no dependency); intent_detected
is deliberately omitted — it needs an intent_enum that only Phase 2 defines,
and adding a column for an enum that doesn't exist yet is exactly the kind
of mid-story schema addition CLAUDE.md rules out (docs/drift.md).

Also widens uq_background_tasks_job_active (US-18's widened index) to admit
CALENDAR_SYNC as a third "no more than one active task per job" task type,
using the same fail-loudly conflict pre-check as
c2d3e4f5a6b7_widen_task_active_index.py. EMAIL_DISPATCH is per-slot, not
per-job, so it is intentionally not part of this guard — its own
idempotency is the email_logs UNIQUE key (see the next migration).

And adds background_tasks.result_summary (JSONB, nullable) — TC-04 requires
"more candidates than slots" to be reported explicitly rather than silently
dropped, and the shortfall is only known once the CALENDAR_SYNC task runs.
Nullable and additive: RESUME_PARSE/BATCH_RANKING tasks simply leave it NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: str | Sequence[str] | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_TASK_WHERE = (
    "task_type IN ('RESUME_PARSE', 'BATCH_RANKING') AND status IN ('PENDING', 'RUNNING')"
)
_NEW_TASK_WHERE = (
    "task_type IN ('RESUME_PARSE', 'BATCH_RANKING', 'CALENDAR_SYNC') "
    "AND status IN ('PENDING', 'RUNNING')"
)

_SLOT_STATUSES = ("PENDING", "CONFIRMED", "DECLINED", "RESCHEDULED", "CANCELLED")
_LIVE_STATUSES_WHERE = "status IN ('PENDING', 'CONFIRMED')"

slot_status_enum = sa.Enum(*_SLOT_STATUSES, name="slot_status_enum")


def upgrade() -> None:
    """Upgrade schema."""
    # create_table creates the enum type itself (checkfirst) — a separate
    # explicit .create() call first would double-create it and fail.
    op.create_table(
        "interview_slots",
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recruiter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("google_calendar_event_id", sa.String(255), nullable=True),
        sa.Column("google_meet_link", sa.Text(), nullable=True),
        sa.Column(
            "status",
            slot_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("candidate_reply_text", sa.Text(), nullable=True),
        sa.Column("reschedule_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "uq_interview_slots_candidate_live",
        "interview_slots",
        ["candidate_id"],
        unique=True,
        postgresql_where=sa.text(_LIVE_STATUSES_WHERE),
    )
    op.create_index(
        "uq_interview_slots_recruiter_time",
        "interview_slots",
        ["recruiter_id", "scheduled_at"],
        unique=True,
        postgresql_where=sa.text(_LIVE_STATUSES_WHERE),
    )

    # Widen the active-task guard, same fail-loudly pre-check as US-18's widening.
    conflicts = (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            SELECT job_id FROM background_tasks
            WHERE {_NEW_TASK_WHERE}
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
        postgresql_where=sa.text(_NEW_TASK_WHERE),
    )

    op.add_column(
        "background_tasks", sa.Column("result_summary", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("background_tasks", "result_summary")

    op.drop_index("uq_background_tasks_job_active", table_name="background_tasks")
    op.create_index(
        "uq_background_tasks_job_active",
        "background_tasks",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text(_OLD_TASK_WHERE),
    )

    op.drop_index("uq_interview_slots_recruiter_time", table_name="interview_slots")
    op.drop_index("uq_interview_slots_candidate_live", table_name="interview_slots")
    op.drop_table("interview_slots")
    slot_status_enum.drop(op.get_bind(), checkfirst=True)
