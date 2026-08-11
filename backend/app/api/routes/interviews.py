import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import fixtures
from app.api.deps import get_current_recruiter
from app.schemas.common import Page, PaginationParams, error_responses, paginate, pagination_params
from app.schemas.enums import SlotStatus
from app.schemas.scheduling import InterviewCreate, InterviewSlotOut, InterviewSlotUpdate
from app.schemas.task import TaskOut

router = APIRouter(
    prefix="/interviews",
    tags=["interviews"],
    dependencies=[Depends(get_current_recruiter)],
)


def _to_slot_out(slot: dict) -> InterviewSlotOut:
    return InterviewSlotOut(**slot, candidate_name=fixtures.candidate_name(slot["candidate_id"]))


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(401, 404, 422),
)
def schedule_interviews(payload: InterviewCreate) -> TaskOut:
    # STUB: US-26 — batch/async, 202 TaskOut polled at GET /tasks/{id} (ADR-004 P4).
    if payload.job_id not in fixtures.JOBS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Job not found."},
        )
    return TaskOut(**fixtures.TASKS[fixtures.TASK_RUNNING_ID])


@router.get("", response_model=Page[InterviewSlotOut], responses=error_responses(401))
def list_interviews(
    job_id: uuid.UUID | None = Query(default=None),
    status_filter: SlotStatus | None = Query(default=None, alias="status"),
    params: PaginationParams = Depends(pagination_params),
) -> Page[InterviewSlotOut]:
    # STUB: US-26 — cross-job master schedule, top-level with ?job_id= (ADR-004 P2).
    slots = list(fixtures.INTERVIEW_SLOTS.values())
    if job_id is not None:
        slots = [s for s in slots if s["job_id"] == job_id]
    if status_filter is not None:
        slots = [s for s in slots if s["status"] == status_filter]
    return paginate([_to_slot_out(s) for s in slots], params)


@router.patch(
    "/{slot_id}", response_model=InterviewSlotOut, responses=error_responses(401, 404, 422)
)
def update_interview(slot_id: uuid.UUID, payload: InterviewSlotUpdate) -> InterviewSlotOut:
    # STUB: US-26 — cancel and reschedule are both PATCH.
    slot = fixtures.INTERVIEW_SLOTS.get(slot_id)
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SLOT_NOT_FOUND", "message": "Interview slot not found."},
        )
    updated = dict(slot)
    if payload.status is not None:
        updated["status"] = payload.status
    if payload.scheduled_at is not None:
        updated["scheduled_at"] = payload.scheduled_at
    return _to_slot_out(updated)
