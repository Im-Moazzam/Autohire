from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db
from app.models.recruiter import Recruiter
from app.schemas.common import error_responses
from app.schemas.recruiter import RecruiterOut, RecruiterUpdate

router = APIRouter(prefix="/recruiters", tags=["recruiters"])


@router.patch("/me", response_model=RecruiterOut, responses=error_responses(401))
def update_me(
    payload: RecruiterUpdate,
    db: Session = Depends(get_db),
    recruiter: Recruiter = Depends(get_current_recruiter),
) -> Recruiter:
    recruiter.full_name = payload.full_name
    db.commit()
    db.refresh(recruiter)
    return recruiter
