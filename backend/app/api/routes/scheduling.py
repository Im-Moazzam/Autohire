import uuid

from fastapi import APIRouter, Depends, Query

from app.api import fixtures
from app.api.deps import get_current_recruiter
from app.schemas.common import error_responses
from app.schemas.scheduling import (
    AvailableSlotOut,
    SchedulingPreferencesIn,
    SchedulingPreferencesOut,
)

router = APIRouter(
    prefix="/scheduling",
    tags=["scheduling"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("/preferences", response_model=SchedulingPreferencesOut, responses=error_responses(401))
def get_preferences() -> SchedulingPreferencesOut:
    # STUB: US-24
    return SchedulingPreferencesOut(**fixtures.SCHEDULING_PREFERENCES)


@router.put(
    "/preferences",
    response_model=SchedulingPreferencesOut,
    responses=error_responses(401, 422),
)
def update_preferences(payload: SchedulingPreferencesIn) -> SchedulingPreferencesOut:
    # STUB: US-24 — singleton, PUT (ADR-004 P6).
    return SchedulingPreferencesOut(
        preference_id=fixtures.PREFERENCE_ID,
        last_synced_at=fixtures.SCHEDULING_PREFERENCES["last_synced_at"],
        **payload.model_dump(),
    )


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
