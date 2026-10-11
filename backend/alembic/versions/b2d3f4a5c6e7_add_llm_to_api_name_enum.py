"""add LLM to api_name_enum

Revision ID: b2d3f4a5c6e7
Revises: a1c2e3f4b5d6
Create Date: 2026-10-10 16:31:00.000000

TS-15's analyzer writes an api_usage_logs row per call (architecture.md: adapters
are the single place usage is counted), which needs an enum value to file it
under. One generic LLM value rather than GEMINI/XAI/GROQ: the adapter speaks a
single OpenAI-compatible wire format to whichever provider LLM_BASE_URL names,
that is app-wide config, and api_usage_logs has no provider-detail column to
split on. Specific values stay a one-line ADD VALUE later (drift row 16).

No downgrade: removing a value from a Postgres enum requires recreating the type
and every dependent column. Carrying an unused value is the cheap direction, same
reasoning the original api_usage_logs migration recorded for PINECONE.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d3f4a5c6e7"
down_revision: str | Sequence[str] | None = "a1c2e3f4b5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # IF NOT EXISTS so a re-run on a partially migrated dev database is a no-op
    # rather than a hard failure.
    op.execute("ALTER TYPE api_name_enum ADD VALUE IF NOT EXISTS 'LLM'")


def downgrade() -> None:
    """Downgrade schema."""
    # Intentionally a no-op — see the module docstring. An unused enum value is
    # inert; recreating the type to drop it would rewrite every dependent column.
    pass
