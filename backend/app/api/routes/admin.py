import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.models.recruiter import Recruiter
from app.schemas.admin import AdminRecruiterOut, AdminTaskOut
from app.schemas.common import Page, PaginationParams, error_responses, pagination_params
from app.schemas.enums import TaskStatus, TaskType
from app.schemas.recruiter import RecruiterOut
from app.services import admin_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


@router.get(
    "/recruiters", response_model=Page[AdminRecruiterOut], responses=error_responses(401, 403)
)
def list_recruiters(
    params: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> Page[AdminRecruiterOut]:
    rows, total = admin_service.list_recruiters(db, params)
    return Page[AdminRecruiterOut](
        items=[
            AdminRecruiterOut(
                id=recruiter.recruiter_id,
                email=recruiter.email,
                name=recruiter.full_name,
                account_state=recruiter.account_state,
                created_at=recruiter.created_at,
                last_login_at=recruiter.last_login_at,
                total_jobs=total_jobs,
                total_candidates=total_candidates,
                total_interviews=total_interviews,
                total_emails=total_emails,
            )
            for recruiter, total_jobs, total_candidates, total_interviews, total_emails in rows
        ],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/tasks", response_model=Page[AdminTaskOut], responses=error_responses(401, 403))
def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    task_type: TaskType | None = Query(default=None),
    params: PaginationParams = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> Page[AdminTaskOut]:
    rows, total = admin_service.list_tasks(db, params, status_filter, task_type)
    return Page[AdminTaskOut](
        items=[
            AdminTaskOut(
                task_id=task.task_id,
                recruiter_id=task.recruiter_id,
                recruiter_email=recruiter_email,
                task_type=task.task_type,
                status=task.status,
                started_at=task.started_at,
                completed_at=task.completed_at,
                error_message=task.error_message,
            )
            for task, recruiter_email in rows
        ],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "/recruiters/{recruiter_id}/suspend",
    response_model=RecruiterOut,
    responses=error_responses(401, 403, 404),
)
def suspend_recruiter(
    recruiter_id: uuid.UUID,
    admin: Recruiter = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Recruiter:
    if recruiter_id == admin.recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CANNOT_SUSPEND_SELF",
                "message": "You can't suspend your own account.",
            },
        )
    recruiter = admin_service.suspend_recruiter(db, recruiter_id)
    if recruiter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RECRUITER_NOT_FOUND", "message": "Recruiter not found."},
        )
    return recruiter


@router.post(
    "/recruiters/{recruiter_id}/reactivate",
    response_model=RecruiterOut,
    responses=error_responses(401, 403, 404),
)
def reactivate_recruiter(
    recruiter_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Recruiter:
    recruiter = admin_service.reactivate_recruiter(db, recruiter_id)
    if recruiter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RECRUITER_NOT_FOUND", "message": "Recruiter not found."},
        )
    return recruiter
