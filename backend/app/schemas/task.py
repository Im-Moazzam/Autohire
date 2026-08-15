import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import TaskStatus, TaskType


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: uuid.UUID
    task_type: TaskType
    status: TaskStatus
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None


class ProcessStatusOut(BaseModel):
    """total/processed/failed are computed over candidates.submission_status —
    there are no such columns on any table."""

    status: TaskStatus
    total: int
    processed: int
    failed: int
    error_message: str | None
