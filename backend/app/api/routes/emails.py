import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api import fixtures
from app.api.deps import get_current_recruiter
from app.schemas.common import Page, PaginationParams, error_responses, paginate, pagination_params
from app.schemas.email import EmailLogOut, EmailSendIn
from app.schemas.enums import EmailType
from app.schemas.task import TaskOut

router = APIRouter(
    prefix="/emails",
    tags=["emails"],
    dependencies=[Depends(get_current_recruiter)],
)


def _to_email_out(email: dict) -> EmailLogOut:
    return EmailLogOut(**email, candidate_name=fixtures.candidate_name(email["candidate_id"]))


@router.post(
    "/send",
    response_model=TaskOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses=error_responses(401, 422),
)
def send_email(payload: EmailSendIn) -> TaskOut:
    # STUB: US-27 — batch/async, 202 TaskOut polled at GET /tasks/{id} (ADR-004 P4).
    del payload
    return TaskOut(**fixtures.TASKS[fixtures.TASK_RUNNING_ID])


@router.get("", response_model=Page[EmailLogOut], responses=error_responses(401))
def list_emails(
    job_id: uuid.UUID | None = Query(default=None),
    candidate_id: uuid.UUID | None = Query(default=None),
    email_type: EmailType | None = Query(default=None),
    params: PaginationParams = Depends(pagination_params),
) -> Page[EmailLogOut]:
    # STUB: US-27 — cross-job history, top-level with ?job_id= (ADR-004 P2).
    emails = list(fixtures.EMAIL_LOGS.values())
    if job_id is not None:
        emails = [e for e in emails if e["job_id"] == job_id]
    if candidate_id is not None:
        emails = [e for e in emails if e["candidate_id"] == candidate_id]
    if email_type is not None:
        emails = [e for e in emails if e["email_type"] == email_type]
    return paginate([_to_email_out(e) for e in emails], params)
