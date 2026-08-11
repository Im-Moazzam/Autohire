import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import fixtures
from app.api.deps import get_current_recruiter
from app.schemas.common import error_responses
from app.schemas.task import TaskOut

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("/{task_id}", response_model=TaskOut, responses=error_responses(401, 404))
def get_task(task_id: uuid.UUID) -> TaskOut:
    # STUB: shared — the poll target for every 202 response (ADR-004 P4).
    task = fixtures.TASKS.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_NOT_FOUND", "message": "Task not found."},
        )
    return TaskOut(**task)
