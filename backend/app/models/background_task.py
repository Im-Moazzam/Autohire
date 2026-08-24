import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum

from app.core.db import Base
from app.schemas.enums import TaskStatus, TaskType


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_postings.job_id", ondelete="CASCADE"), nullable=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.candidate_id", ondelete="CASCADE"), nullable=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type_enum", native_enum=True), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum", native_enum=True),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    # TC-04 (US-26): {scheduled, unscheduled: [{candidate_id, full_name, reason}],
    # horizon_days} for CALENDAR_SYNC. Nullable and additive — RESUME_PARSE and
    # BATCH_RANKING tasks leave this NULL.
    result_summary: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
