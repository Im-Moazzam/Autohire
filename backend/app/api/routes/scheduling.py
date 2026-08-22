import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import fixtures
from app.api.deps import get_current_recruiter, get_db
from app.models.recruiter import Recruiter
from app.schemas.common import error_responses
from app.schemas.scheduling import (
    AvailableSlotOut,
    SchedulingPreferencesIn,
    SchedulingPreferencesOut,
)
from app.services import scheduling_service

router = APIRouter(
    prefix="/scheduling",
    tags=["scheduling"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("/preferences", response_model=SchedulingPreferencesOut, responses=error_responses(401))
def get_preferences(
    db: Session = Depends(get_db),
    recruiter: Recruiter = Depends(get_current_recruiter),
) -> SchedulingPreferencesOut:
    # Never 404 — GET before any PUT returns synthesized defaults (US-24).
    return scheduling_service.get_preferences(db, recruiter.recruiter_id)


@router.put(
    "/preferences",
    response_model=SchedulingPreferencesOut,
    responses=error_responses(401, 422),
)
def update_preferences(
    payload: SchedulingPreferencesIn,
    db: Session = Depends(get_db),
    recruiter: Recruiter = Depends(get_current_recruiter),
) -> SchedulingPreferencesOut:
    # Upsert — one row per recruiter, ever. Never 409 on "already exists" (US-24).
    row = scheduling_service.upsert_preferences(db, recruiter.recruiter_id, payload)
    return SchedulingPreferencesOut.model_validate(row)


@router.get(
    "/available-slots",
    response_model=list[AvailableSlotOut],
    responses=error_responses(401, 404, 409),
)
def available_slots(
    job_id: uuid.UUID | None = Query(default=None),
    count: int = Query(default=10, ge=1, le=50),
) -> list[AvailableSlotOut]:
    # STUB: US-26 — computed and bounded by count, not Page[T] (ADR-004 P5).
    # job_id narrows against the job's recruiter's calendar once real; unused in the stub.
    del job_id
    return [AvailableSlotOut(**slot) for slot in fixtures.AVAILABLE_SLOTS[:count]]
