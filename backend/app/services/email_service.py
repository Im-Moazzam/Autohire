import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.schemas.common import PaginationParams
from app.schemas.enums import EmailType


def render_invite(
    candidate: Candidate, job: JobPosting, slot: InterviewSlot, timezone: str
) -> tuple[str, str]:
    """One template, not a template system — a template system is Phase 2.
    Candidate name, job title, date/time (in the recruiter's saved
    timezone), duration, and the Meet link. Returns (subject, body)."""
    local_time = slot.scheduled_at.astimezone(ZoneInfo(timezone))
    when = local_time.strftime("%A, %B %d, %Y at %I:%M %p %Z")

    subject = f"Interview invitation: {job.job_title}"
    lines = [
        f"Hi {candidate.full_name},",
        "",
        f"You're invited to interview for {job.job_title}.",
        "",
        f"When: {when}",
        f"Duration: {slot.duration_minutes} minutes",
    ]
    if slot.google_meet_link:
        lines.append(f"Join: {slot.google_meet_link}")
    lines += ["", "Looking forward to speaking with you."]
    return subject, "\n".join(lines)


def list_emails(
    db: Session,
    recruiter_id: uuid.UUID,
    params: PaginationParams,
    job_id: uuid.UUID | None,
    candidate_id: uuid.UUID | None,
    email_type: EmailType | None,
) -> tuple[list[tuple[EmailLog, str]], int]:
    """email_logs has no job_id column — job_id filters through the
    candidate join, same as the story's ?job_id= convention elsewhere."""
    base = (
        select(EmailLog, Candidate.full_name)
        .join(Candidate, Candidate.candidate_id == EmailLog.candidate_id)
        .where(EmailLog.recruiter_id == recruiter_id)
    )
    if job_id is not None:
        base = base.where(Candidate.job_id == job_id)
    if candidate_id is not None:
        base = base.where(EmailLog.candidate_id == candidate_id)
    if email_type is not None:
        base = base.where(EmailLog.email_type == email_type)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(EmailLog.sent_at.desc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return [(row[0], row[1]) for row in rows], total
