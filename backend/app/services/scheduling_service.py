import uuid
from datetime import time

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.scheduling import SchedulingPreference
from app.schemas.enums import Weekday
from app.schemas.scheduling import SchedulingPreferencesIn, SchedulingPreferencesOut

_WRITE_FAILED = {
    "code": "SCHEDULING_WRITE_FAILED",
    "message": "Availability preferences could not be saved.",
}

DEFAULT_DAYS = [
    Weekday.MONDAY,
    Weekday.TUESDAY,
    Weekday.WEDNESDAY,
    Weekday.THURSDAY,
    Weekday.FRIDAY,
]
DEFAULT_START_TIME = time(9, 0)
DEFAULT_END_TIME = time(17, 0)
DEFAULT_SLOT_DURATION_MINUTES = 30


def _get_row(db: Session, recruiter_id: uuid.UUID) -> SchedulingPreference | None:
    return db.scalar(
        select(SchedulingPreference).where(SchedulingPreference.recruiter_id == recruiter_id)
    )


def get_preferences(db: Session, recruiter_id: uuid.UUID) -> SchedulingPreferencesOut:
    row = _get_row(db, recruiter_id)
    if row is not None:
        return SchedulingPreferencesOut.model_validate(row)
    # No row yet: synthesize defaults rather than writing one. A read stays a
    # read — "a row exists" then honestly means "the recruiter set this".
    return SchedulingPreferencesOut(
        preference_id=None,
        available_days=DEFAULT_DAYS,
        available_start_time=DEFAULT_START_TIME,
        available_end_time=DEFAULT_END_TIME,
        slot_duration_minutes=DEFAULT_SLOT_DURATION_MINUTES,
        timezone=settings.scheduling_timezone,
        last_synced_at=None,
    )


def upsert_preferences(
    db: Session, recruiter_id: uuid.UUID, payload: SchedulingPreferencesIn
) -> SchedulingPreference:
    row = _get_row(db, recruiter_id)
    if row is None:
        row = SchedulingPreference(
            recruiter_id=recruiter_id,
            # Set once, at creation, from the live setting. Never touched again
            # by an update, so this row keeps meaning what it meant when it was
            # entered even if SCHEDULING_TIMEZONE changes afterward.
            timezone=settings.scheduling_timezone,
        )
        db.add(row)

    row.available_days = [day.value for day in payload.available_days]
    row.available_start_time = payload.available_start_time
    row.available_end_time = payload.available_end_time
    row.slot_duration_minutes = payload.slot_duration_minutes

    _commit(db, row)
    return row


def _commit(db: Session, row: SchedulingPreference) -> None:
    """The four CHECK constraints on this table are invariants-of-last-resort —
    SchedulingPreferencesIn's validators reject anything that would trip them
    before a row is ever built, so this path is not expected to be reachable
    through the API. If it ever is (a bad migration, a future direct write),
    fail loudly rather than leak a raw IntegrityError."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_WRITE_FAILED
        ) from None
    db.refresh(row)
