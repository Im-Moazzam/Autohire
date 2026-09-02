from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db
from app.models.recruiter import Recruiter
from app.schemas.common import error_responses
from app.schemas.dashboard import DashboardStatsOut
from app.services import dashboard_service

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("/stats", response_model=DashboardStatsOut, responses=error_responses(401))
def get_stats(
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> DashboardStatsOut:
    return dashboard_service.get_dashboard_stats(db, recruiter.recruiter_id)
