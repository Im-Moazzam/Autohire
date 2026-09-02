from pydantic import BaseModel

from app.schemas.enums import DeliveryStatus, JobStatus, SlotStatus, SubmissionStatus


class DashboardStatsOut(BaseModel):
    """Recruiter-scoped counts across every table the dashboard needs — each
    breakdown is zero-filled across its full enum (dashboard_service), so the
    frontend never has to guess whether a missing key means zero or an
    omission."""

    total_jobs: int
    total_candidates: int
    total_interviews: int
    total_emails: int
    jobs_by_status: dict[JobStatus, int]
    candidates_by_status: dict[SubmissionStatus, int]
    interviews_by_status: dict[SlotStatus, int]
    emails_by_status: dict[DeliveryStatus, int]
