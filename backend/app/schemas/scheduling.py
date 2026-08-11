import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.enums import SlotStatus, Weekday


class SchedulingPreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preference_id: uuid.UUID
    available_days: list[Weekday]
    available_start_time: time
    available_end_time: time
    slot_duration_minutes: int
    last_synced_at: datetime | None


class SchedulingPreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_days: list[Weekday]
    available_start_time: time
    available_end_time: time
    slot_duration_minutes: int

    @model_validator(mode="after")
    def _check_window(self) -> "SchedulingPreferencesIn":
        if self.available_start_time >= self.available_end_time:
            raise ValueError("available_start_time must be before available_end_time")
        return self


class AvailableSlotOut(BaseModel):
    """Computed and bounded by ?count=, never Page[T] (ADR-004 P5)."""

    starts_at: datetime
    ends_at: datetime


class InterviewSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slot_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    job_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    status: SlotStatus
    google_meet_link: str | None


class InterviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID
    candidate_ids: list[uuid.UUID]


class InterviewSlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SlotStatus | None = None
    scheduled_at: datetime | None = None
    reschedule_reason: str | None = None
