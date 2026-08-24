import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db
from app.models.candidate import Candidate
from app.models.recruiter import Recruiter
from app.schemas.common import Page, PaginationParams, error_responses, pagination_params
from app.schemas.enums import SlotStatus
from app.schemas.scheduling import InterviewCreate, InterviewSlotOut, InterviewSlotUpdate
from app.schemas.task import TaskOut
from app.services import interview_service

router = APIRouter(
    prefix="/interviews",
    tags=["interviews"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(401, 404, 409, 422),
)
def schedule_interviews(
    payload: InterviewCreate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = interview_service.enqueue_scheduling(
        db, recruiter, payload.job_id, payload.candidate_ids
    )
    return TaskOut.model_validate(task)


@router.get("", response_model=Page[InterviewSlotOut], responses=error_responses(401))
def list_interviews(
    job_id: uuid.UUID | None = Query(default=None),
    status_filter: SlotStatus | None = Query(default=None, alias="status"),
    params: PaginationParams = Depends(pagination_params),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> Page[InterviewSlotOut]:
    slots, total = interview_service.list_slots(
        db, recruiter.recruiter_id, params, job_id, status_filter
    )
    names = _candidate_names(db, [slot.candidate_id for slot in slots])
    return Page[InterviewSlotOut](
        items=[
            InterviewSlotOut(
                slot_id=slot.slot_id,
                candidate_id=slot.candidate_id,
                candidate_name=names.get(slot.candidate_id, ""),
                job_id=slot.job_id,
                scheduled_at=slot.scheduled_at,
                duration_minutes=slot.duration_minutes,
                status=slot.status,
                google_meet_link=slot.google_meet_link,
            )
            for slot in slots
        ],
        total=total,
        page=params.page,
        size=params.size,
    )


def _candidate_names(db: Session, candidate_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not candidate_ids:
        return {}
    rows = db.execute(
        select(Candidate.candidate_id, Candidate.full_name).where(
            Candidate.candidate_id.in_(candidate_ids)
        )
    ).all()
    return {candidate_id: full_name for candidate_id, full_name in rows}


@router.patch(
    "/{slot_id}",
    response_model=InterviewSlotOut,
    responses=error_responses(401, 404, 422, 501),
)
def update_interview(slot_id: uuid.UUID, payload: InterviewSlotUpdate) -> InterviewSlotOut:
    # Genuinely Phase 2 (cancel/reschedule) — honest 501, not a fixture lookup
    # that 404s on every real slot (TS-06/R-04).
    del slot_id, payload
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Rescheduling and cancelling interviews is Phase 2 and is not implemented.",
        },
    )
