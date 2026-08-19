"""create candidates and candidate_form_responses

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

submission_status_enum = sa.Enum(
    "SUBMITTED",
    "PARSED",
    "RANKED",
    "INVITED",
    "CONFIRMED",
    "DECLINED",
    "REJECTED",
    "RESCHEDULED",
    "PARSE_ERROR",
    name="submission_status_enum",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "candidates",
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_postings.job_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(30), nullable=True),
        sa.Column("resume_drive_file_id", sa.String(255), nullable=True),
        sa.Column("resume_drive_url", sa.Text(), nullable=True),
        sa.Column("resume_storage_key", sa.String(500), nullable=True),
        sa.Column(
            "submission_status",
            submission_status_enum,
            nullable=False,
            server_default="SUBMITTED",
        ),
        sa.Column(
            "submitted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Partial, not plain UNIQUE: a soft-deleted candidate must free up its email
    # for a re-application to the same job, same precedent as US-04's
    # uq_form_templates_name WHERE deleted_at IS NULL.
    op.create_index(
        "uq_candidates_job_email",
        "candidates",
        ["job_id", "email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_candidates_job_status", "candidates", ["job_id", "submission_status"])

    op.create_table(
        "candidate_form_responses",
        sa.Column(
            "response_id",
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
            "field_id",
            postgresql.UUID(as_uuid=True),
            # No ondelete: template_fields are reconciled by id (US-04), not
            # deleted-and-recreated, so this FK should stay intact across saves.
            sa.ForeignKey("template_fields.field_id"),
            nullable=False,
        ),
        sa.Column("response_value", sa.Text(), nullable=True),
    )
    op.create_index(
        "uq_candidate_form_responses_field",
        "candidate_form_responses",
        ["candidate_id", "field_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_candidate_form_responses_field", table_name="candidate_form_responses")
    op.drop_table("candidate_form_responses")
    op.drop_index("ix_candidates_job_status", table_name="candidates")
    op.drop_index("uq_candidates_job_email", table_name="candidates")
    op.drop_table("candidates")
    submission_status_enum.drop(op.get_bind(), checkfirst=True)
