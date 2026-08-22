import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.enums import SlotStatus, Weekday

_WEEKDAY_ORDER = {
    day: i
    for i, day in enumerate(
        ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    )
}


class SchedulingPreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preference_id: uuid.UUID | None  # None == synthesized defaults; nothing saved yet
    available_days: list[Weekday]
    available_start_time: time
    available_end_time: time
    slot_duration_minutes: int
    timezone: str  # persisted on the row at write time; see scheduling_service
    last_synced_at: datetime | None


class SchedulingPreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_days: list[Weekday] = Field(min_length=1)
    available_start_time: time
    available_end_time: time
    slot_duration_minutes: int = Field(ge=15, le=120)

    @field_validator("available_days", mode="before")
    @classmethod
    def _normalize_days(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        upper = [v.upper() if isinstance(v, str) else v for v in value]
        deduped = list(dict.fromkeys(upper))

        def _sort_key(day: object) -> int:
            return _WEEKDAY_ORDER.get(day, len(_WEEKDAY_ORDER)) if isinstance(day, str) else -1

        return sorted(deduped, key=_sort_key)

    @model_validator(mode="after")
    def _check_window(self) -> "SchedulingPreferencesIn":
        if self.available_start_time >= self.available_end_time:
            raise ValueError("available_start_time must be before available_end_time")
        window_minutes = (
            datetime.combine(datetime.min, self.available_end_time)
            - datetime.combine(datetime.min, self.available_start_time)
        ).total_seconds() / 60
        if self.slot_duration_minutes > window_minutes:
            raise ValueError(
                f"slot_duration_minutes ({self.slot_duration_minutes}) does not fit the "
                f"{int(window_minutes)}-minute window between available_start_time and "
                "available_end_time"
            )
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
