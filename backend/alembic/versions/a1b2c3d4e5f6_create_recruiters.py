"""create recruiters

Revision ID: a1b2c3d4e5f6
Revises: 112c34b8ee71
Create Date: 2026-08-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "112c34b8ee71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

recruiter_state_enum = sa.Enum(
    "ACTIVE", "SUSPENDED", "REAUTH_REQUIRED", name="recruiter_state_enum"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recruiters",
        sa.Column(
            "recruiter_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("google_user_id", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("profile_picture_url", sa.Text(), nullable=True),
        sa.Column("google_access_token", sa.Text(), nullable=False),
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
        sa.Column("google_token_expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("granted_scopes", postgresql.JSONB(), nullable=False),
        sa.Column(
            "account_state",
            recruiter_state_enum,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("recruiters")
    recruiter_state_enum.drop(op.get_bind(), checkfirst=True)
