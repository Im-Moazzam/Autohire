import uuid
from datetime import datetime, time

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# available_days is VARCHAR[]; <@ needs matching array element types, so both
# sides are cast to text[] (see the migration for the operator error this avoids).
_DAYS_VALID = (
    "cardinality(available_days) > 0 AND available_days::text[] <@ ARRAY["
    "'MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY']::text[]"
)


class SchedulingPreference(Base):
    __tablename__ = "scheduling_preferences"
    __table_args__ = (
        CheckConstraint(
            "available_start_time < available_end_time", name="ck_scheduling_preferences_window"
        ),
        CheckConstraint(_DAYS_VALID, name="ck_scheduling_preferences_days_valid"),
        CheckConstraint(
            "slot_duration_minutes BETWEEN 15 AND 120",
            name="ck_scheduling_preferences_slot_duration",
        ),
    )

    preference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    available_days: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False)
    available_start_time: Mapped[time] = mapped_column(Time(), nullable=False)
    available_end_time: Mapped[time] = mapped_column(Time(), nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer(), nullable=False, default=30)
    # Set once, at insert, from settings.scheduling_timezone — never overwritten by a
    # later update, so a saved row keeps meaning what it meant when it was entered
    # even if the app-wide setting changes afterward.
    timezone: Mapped[str] = mapped_column(String(), nullable=False)
    # Reserved: always NULL today — nothing writes a real value (US-26's
    # calendar work may populate it later). Already in the generated client
    # contract, so kept rather than dropped (TS-06/R-09).
    last_synced_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
