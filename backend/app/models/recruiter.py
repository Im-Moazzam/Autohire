import enum
import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RecruiterState(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REAUTH_REQUIRED = "REAUTH_REQUIRED"


class Recruiter(Base):
    __tablename__ = "recruiters"

    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    google_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    profile_picture_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    google_access_token: Mapped[str] = mapped_column(Text(), nullable=False)
    google_refresh_token: Mapped[str | None] = mapped_column(Text(), nullable=True)
    google_token_expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    granted_scopes: Mapped[list[str]] = mapped_column(JSONB(), nullable=False)
    account_state: Mapped[RecruiterState] = mapped_column(
        Enum(RecruiterState, name="recruiter_state_enum", native_enum=True),
        nullable=False,
        default=RecruiterState.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
