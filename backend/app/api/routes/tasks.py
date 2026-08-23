import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db
from app.models.recruiter import Recruiter
from app.schemas.common import error_responses
from app.schemas.task import TaskOut
from app.services import task_service

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("/{task_id}", response_model=TaskOut, responses=error_responses(401, 404))
def get_task(
    task_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = task_service.get_task(db, recruiter.recruiter_id, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "Task not found."},
        )
    return TaskOut.model_validate(task)
