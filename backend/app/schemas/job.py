import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator

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
    apply_url: str


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

    @field_validator("expires_at")
    @classmethod
    def _expires_in_future(cls, value: datetime) -> datetime:
        # Naive datetimes are treated as UTC rather than blowing up the
        # comparison against an aware "now".
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        if aware <= datetime.now(UTC):
            raise ValueError("expires_at must be in the future")
        return value


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str | None = None
    job_description: str | None = None
    expires_at: datetime | None = None
    is_accepting_responses: bool | None = None
    status: JobStatus | None = None
