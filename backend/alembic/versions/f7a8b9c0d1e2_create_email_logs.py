"""create email_logs

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-08-23 12:00:01.000000

US-27. idempotency_key = "{candidate_id}:{email_type}:{slot_id or 'none'}",
UNIQUE — this constraint IS the dedupe design (story AC): a retried
EMAIL_DISPATCH task's insert hits this constraint and no-ops rather than
sending twice. No application-level dedupe on top of it.

email_type_enum and delivery_status_enum are built from the full
app.schemas.enums.EmailType / DeliveryStatus members, not the two email
types docs/schema.md happens to list — the Python enum (six members) is
already the source of truth used across the codebase (docs/drift.md).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMAIL_TYPES = (
    "APPLICATION_CONFIRMATION",
    "INTERVIEW_INVITE",
    "INTERVIEW_RESCHEDULE",
    "CANCELLATION",
    "REJECTION",
    "CUSTOM",
)
_DELIVERY_STATUSES = ("SENT", "FAILED", "PENDING")

email_type_enum = sa.Enum(*_EMAIL_TYPES, name="email_type_enum")
delivery_status_enum = sa.Enum(*_DELIVERY_STATUSES, name="delivery_status_enum")


def upgrade() -> None:
    """Upgrade schema."""
    # create_table creates both enum types itself (checkfirst) — a separate
    # explicit .create() call first would double-create them and fail.
    op.create_table(
        "email_logs",
        sa.Column(
            "email_id",
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
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interview_slots.slot_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email_type", email_type_enum, nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body_preview", sa.Text(), nullable=True),
        sa.Column("gmail_message_id", sa.String(255), nullable=True),
        sa.Column("gmail_thread_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("delivery_status", delivery_status_enum, nullable=False),
        sa.Column("is_automated", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index(
        "uq_email_logs_idempotency_key",
        "email_logs",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_email_logs_idempotency_key", table_name="email_logs")
    op.drop_table("email_logs")
    delivery_status_enum.drop(op.get_bind(), checkfirst=True)
    email_type_enum.drop(op.get_bind(), checkfirst=True)
