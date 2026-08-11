import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import JobStatus, SubmissionStatus


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    job_title: str
    status: JobStatus
    is_accepting_responses: bool
    expires_at: datetime
    submission_count: int
    created_at: datetime


class JobDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    job_title: str
    status: JobStatus
    is_accepting_responses: bool
    expires_at: datetime
    submission_count: int
    created_at: datetime
    job_description: str
    template_id: uuid.UUID
    apply_slug: str
    apply_url: str
    google_drive_folder_id: str | None
    updated_at: datetime
    submission_counts: dict[SubmissionStatus, int]


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str
    job_description: str
    template_id: uuid.UUID
    expires_at: datetime


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str | None = None
    job_description: str | None = None
    expires_at: datetime | None = None
    is_accepting_responses: bool | None = None
    status: JobStatus | None = None
