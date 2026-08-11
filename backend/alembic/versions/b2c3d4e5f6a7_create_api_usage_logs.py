"""create api_usage_logs

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# PINECONE omitted: dropped per docs/drift.md row 10. Adding an enum value later
# is a one-line ALTER TYPE; carrying an unused one is the expensive direction.
api_name_enum = sa.Enum(
    "GOOGLE_DRIVE", "GOOGLE_GMAIL", "GOOGLE_CALENDAR", "OPENAI", name="api_name_enum"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "api_usage_logs",
        sa.Column(
            "log_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "recruiter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recruiters.recruiter_id"),
            nullable=True,
        ),
        sa.Column("api_name", api_name_enum, nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("api_usage_logs")
    api_name_enum.drop(op.get_bind(), checkfirst=True)
