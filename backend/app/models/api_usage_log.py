import enum
import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ApiName(enum.StrEnum):
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    GOOGLE_GMAIL = "GOOGLE_GMAIL"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    OPENAI = "OPENAI"


class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recruiters.recruiter_id"), nullable=True
    )
    api_name: Mapped[ApiName] = mapped_column(
        Enum(ApiName, name="api_name_enum", native_enum=True), nullable=False
    )
    call_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
