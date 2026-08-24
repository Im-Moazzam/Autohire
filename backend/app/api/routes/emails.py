import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db
from app.models.recruiter import Recruiter
from app.schemas.common import Page, PaginationParams, error_responses, pagination_params
from app.schemas.email import EmailLogOut, EmailSendIn
from app.schemas.enums import EmailType
from app.schemas.task import TaskOut
from app.services import email_service

router = APIRouter(
    prefix="/emails",
    tags=["emails"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.post(
    "/send",
    response_model=TaskOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(401, 422, 501),
)
def send_email(payload: EmailSendIn) -> TaskOut:
    # Manual, ad hoc send is genuinely Phase 2 — only the automatic
    # INTERVIEW_INVITE dispatch (calendar_sync -> email_dispatch) is real.
    # Honest 501, not a stale fixture TaskOut whose task_id 404s at
    # GET /tasks/{id} (TS-06/R-04).
    del payload
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": "Manual email send is Phase 2 and is not implemented.",
        },
    )


@router.get("", response_model=Page[EmailLogOut], responses=error_responses(401))
def list_emails(
    job_id: uuid.UUID | None = Query(default=None),
    candidate_id: uuid.UUID | None = Query(default=None),
    email_type: EmailType | None = Query(default=None),
    params: PaginationParams = Depends(pagination_params),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> Page[EmailLogOut]:
    rows, total = email_service.list_emails(
        db, recruiter.recruiter_id, params, job_id, candidate_id, email_type
    )
    return Page[EmailLogOut](
        items=[
            EmailLogOut(
                email_id=log.email_id,
                candidate_id=log.candidate_id,
                candidate_name=candidate_name,
                email_type=log.email_type,
                subject=log.subject,
                body_preview=log.body_preview,
                delivery_status=log.delivery_status,
                sent_at=log.sent_at,
                is_automated=log.is_automated,
            )
            for log, candidate_name in rows
        ],
        total=total,
        page=params.page,
        size=params.size,
    )
