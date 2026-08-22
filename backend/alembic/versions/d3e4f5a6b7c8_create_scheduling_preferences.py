"""create scheduling_preferences

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-23 00:00:00.000000

US-24. One row per recruiter (`UNIQUE(recruiter_id)`), upserted by
`PUT /scheduling/preferences`. `available_days` is `TEXT[]` rather than a Postgres
enum array (awkward with SQLAlchemy) constrained instead by
`ck_scheduling_preferences_days_valid`. The four CHECK constraints here duplicate
Pydantic validators in `app.schemas.scheduling` deliberately, as invariants-of-last-
resort — the API can never reach them, since Pydantic rejects first. They exist so a
future service, a raw script, or a bad migration can't silently write a broken row.
`timezone` is set once at insert time from `settings.scheduling_timezone` and never
overwritten by later updates — see `scheduling_service.upsert_preferences`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# available_days is VARCHAR[] (postgresql.ARRAY(sa.String())); the <@ containment
# operator requires matching array element types, so both sides are cast to text[].
_DAYS_VALID = (
    "cardinality(available_days) > 0 AND available_days::text[] <@ ARRAY["
    "'MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY']::text[]"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "scheduling_preferences",
        sa.Column(
            "preference_id",
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
        sa.Column("available_days", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("available_start_time", sa.Time(), nullable=False),
        sa.Column("available_end_time", sa.Time(), nullable=False),
        sa.Column(
            "slot_duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("30")
        ),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("last_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "available_start_time < available_end_time", name="ck_scheduling_preferences_window"
        ),
        sa.CheckConstraint(_DAYS_VALID, name="ck_scheduling_preferences_days_valid"),
        sa.CheckConstraint(
            "slot_duration_minutes BETWEEN 15 AND 120",
            name="ck_scheduling_preferences_slot_duration",
        ),
    )
    op.create_index(
        "uq_scheduling_preferences_recruiter",
        "scheduling_preferences",
        ["recruiter_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_scheduling_preferences_recruiter", table_name="scheduling_preferences")
    op.drop_table("scheduling_preferences")
