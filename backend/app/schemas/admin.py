import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.recruiter import RecruiterState
from app.schemas.enums import TaskStatus, TaskType


class AdminRecruiterOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    account_state: RecruiterState
    created_at: datetime
    last_login_at: datetime | None
    total_jobs: int
    total_candidates: int
    total_interviews: int
    total_emails: int


class AdminTaskOut(BaseModel):
    task_id: uuid.UUID
    recruiter_id: uuid.UUID
    recruiter_email: str
    task_type: TaskType
    status: TaskStatus
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
