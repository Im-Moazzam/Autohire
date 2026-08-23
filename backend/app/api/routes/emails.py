import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api import fixtures
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
    responses=error_responses(401, 422),
)
def send_email(payload: EmailSendIn) -> TaskOut:
    # STUB: manual send is out of this story's scope — only the automatic
    # INTERVIEW_INVITE dispatch (calendar_sync -> email_dispatch) is real.
    del payload
    return TaskOut(**fixtures.TASKS[fixtures.TASK_RUNNING_ID])


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
