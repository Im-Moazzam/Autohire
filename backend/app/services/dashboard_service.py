import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.schemas.dashboard import DashboardStatsOut
from app.schemas.enums import DeliveryStatus, JobStatus, SlotStatus, SubmissionStatus


def get_dashboard_stats(db: Session, recruiter_id: uuid.UUID) -> DashboardStatsOut:
    """Four bounded GROUP BY queries, never N+1 over the recruiter's jobs.
    job_postings/interview_slots/email_logs carry recruiter_id directly;
    candidates only has job_id, so that one query joins through job_postings
    — this is the one place a candidate count crosses jobs, mirroring
    job_service.submission_counts_by_job's per-job version but scoped to the
    whole recruiter instead of one job."""
    jobs_by_status: dict[JobStatus, int] = dict.fromkeys(JobStatus, 0)
    for status, count in db.execute(
        select(JobPosting.status, func.count())
        .where(JobPosting.recruiter_id == recruiter_id, JobPosting.deleted_at.is_(None))
        .group_by(JobPosting.status)
    ).all():
        jobs_by_status[status] = count

    candidates_by_status: dict[SubmissionStatus, int] = dict.fromkeys(SubmissionStatus, 0)
    for status, count in db.execute(
        select(Candidate.submission_status, func.count())
        .join(JobPosting, JobPosting.job_id == Candidate.job_id)
        .where(
            JobPosting.recruiter_id == recruiter_id,
            JobPosting.deleted_at.is_(None),
            Candidate.deleted_at.is_(None),
        )
        .group_by(Candidate.submission_status)
    ).all():
        candidates_by_status[status] = count

    interviews_by_status: dict[SlotStatus, int] = dict.fromkeys(SlotStatus, 0)
    for status, count in db.execute(
        select(InterviewSlot.status, func.count())
        .where(InterviewSlot.recruiter_id == recruiter_id)
        .group_by(InterviewSlot.status)
    ).all():
        interviews_by_status[status] = count

    emails_by_status: dict[DeliveryStatus, int] = dict.fromkeys(DeliveryStatus, 0)
    for status, count in db.execute(
        select(EmailLog.delivery_status, func.count())
        .where(EmailLog.recruiter_id == recruiter_id)
        .group_by(EmailLog.delivery_status)
    ).all():
        emails_by_status[status] = count

    return DashboardStatsOut(
        total_jobs=sum(jobs_by_status.values()),
        total_candidates=sum(candidates_by_status.values()),
        total_interviews=sum(interviews_by_status.values()),
        total_emails=sum(emails_by_status.values()),
        jobs_by_status=jobs_by_status,
        candidates_by_status=candidates_by_status,
        interviews_by_status=interviews_by_status,
        emails_by_status=emails_by_status,
    )
