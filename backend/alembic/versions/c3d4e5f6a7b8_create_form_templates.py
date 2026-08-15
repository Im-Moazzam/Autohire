"""create form_templates and template_fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

field_type_enum = sa.Enum(
    "SHORT_TEXT",
    "PARAGRAPH",
    "MULTIPLE_CHOICE",
    "DROPDOWN",
    "FILE_UPLOAD",
    "DATE",
    "NUMBER",
    name="field_type_enum",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "form_templates",
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "recruiter_id",
            postgresql.UUID(as_uuid=True),
            # Recruiters are never hard-deleted (account_state handles
            # deactivation) — this CASCADE is a safety net that should never
            # fire, not a signal that recruiter deletion is a supported flow.
            sa.ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_name", sa.String(150), nullable=False),
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
    op.create_index("ix_form_templates_recruiter_id", "form_templates", ["recruiter_id"])
    op.create_index(
        "uq_form_templates_recruiter_name_active",
        "form_templates",
        ["recruiter_id", "template_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "template_fields",
        sa.Column(
            "field_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("form_templates.template_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_label", sa.String(200), nullable=False),
        sa.Column("field_type", field_type_enum, nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("field_order", sa.Integer(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("template_id", "field_order", name="uq_template_fields_order"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("template_fields")
    op.drop_index("uq_form_templates_recruiter_name_active", table_name="form_templates")
    op.drop_index("ix_form_templates_recruiter_id", table_name="form_templates")
    op.drop_table("form_templates")
    field_type_enum.drop(op.get_bind(), checkfirst=True)
