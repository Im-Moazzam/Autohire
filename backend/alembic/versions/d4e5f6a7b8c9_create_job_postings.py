"""create job_postings

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

job_status_enum = sa.Enum("DRAFT", "LIVE", "CLOSED", "PROCESSED", name="job_status_enum")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "job_postings",
        sa.Column(
            "job_id",
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
            "template_id",
            postgresql.UUID(as_uuid=True),
            # No ondelete (RESTRICT): a CASCADE here would silently destroy
            # jobs when a template is soft-deleted. TEMPLATE_IN_USE guards it.
            sa.ForeignKey("form_templates.template_id"),
            nullable=False,
        ),
        sa.Column("job_title", sa.String(200), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("jd_embedding_id", sa.String(255), nullable=True),
        sa.Column("google_form_id", sa.String(255), nullable=True),
        sa.Column("google_form_url", sa.Text(), nullable=True),
        sa.Column("google_drive_folder_id", sa.String(255), nullable=True),
        sa.Column("apply_slug", sa.String(64), nullable=False),
        sa.Column("status", job_status_enum, nullable=False, server_default="DRAFT"),
        sa.Column("is_accepting_responses", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
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
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("uq_job_postings_apply_slug", "job_postings", ["apply_slug"], unique=True)
    op.create_index("ix_job_postings_recruiter_status", "job_postings", ["recruiter_id", "status"])
    op.create_index(
        "ix_job_postings_expires_at_live",
        "job_postings",
        ["expires_at"],
        postgresql_where=sa.text("status = 'LIVE'"),
    )
    op.create_index("ix_job_postings_template_id", "job_postings", ["template_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_job_postings_template_id", table_name="job_postings")
    op.drop_index("ix_job_postings_expires_at_live", table_name="job_postings")
    op.drop_index("ix_job_postings_recruiter_status", table_name="job_postings")
    op.drop_index("uq_job_postings_apply_slug", table_name="job_postings")
    op.drop_table("job_postings")
    job_status_enum.drop(op.get_bind(), checkfirst=True)
