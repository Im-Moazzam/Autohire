"""Rebuilds a full demo world for local manual/frontend testing: a recruiter,
templates, jobs across every status, candidates across every submission
status (built from real resumes dropped in backend/seed_resumes/, falling
back to the bundled test fixture), rankings, interview slots, and email logs.

    mise run db:seed-demo

Wipes and rebuilds every run (deterministic uuid5 IDs), so it's safe to
re-run after `mise run reset`. Never run this against anything but a local
dev database - see _refuse_unless_local below.
"""

import uuid
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.resume_store import LocalResumeStore
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate, CandidateFormResponse
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.models.scheduling import SchedulingPreference
from app.models.template import FormTemplate, TemplateField
from app.schemas.enums import (
    DeliveryStatus,
    EmailType,
    FieldType,
    JobStatus,
    SlotStatus,
    SubmissionStatus,
    TaskStatus,
    TaskType,
)
from app.scripts.seed import _refuse_unless_local, seed_recruiter
from app.services.resume_parser import extract_text

SEED_RESUMES_DIR = Path(__file__).resolve().parents[2] / "seed_resumes"
FALLBACK_RESUME = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "resumes" / "Moazzam_Resume.pdf"
)

# One archetype per SubmissionStatus so every candidate-list state is reachable.
_ARCHETYPES = [
    SubmissionStatus.SUBMITTED,
    SubmissionStatus.PARSED,
    SubmissionStatus.RANKED,
    SubmissionStatus.RANKED,
    SubmissionStatus.PARSE_ERROR,
    SubmissionStatus.REJECTED,
]

_MATCHED = ["FastAPI", "PostgreSQL", "SQLAlchemy"]
_MISSING = ["Kubernetes"]


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"autohire.seed-demo/{name}")


def _resume_files() -> list[Path]:
    if SEED_RESUMES_DIR.is_dir():
        files = sorted(
            p for p in SEED_RESUMES_DIR.iterdir() if p.suffix.lower() in (".pdf", ".docx")
        )
        if files:
            return files
    return [FALLBACK_RESUME]


def _display_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def _email_for(display_name: str) -> str:
    return display_name.lower().replace(" ", ".") + "@example.com"


def _wipe(db: Session) -> None:
    # FK order, extended from conftest.db_session's teardown with AiAnalysisResult.
    db.query(EmailLog).delete()
    db.query(InterviewSlot).delete()
    db.query(BackgroundTask).delete()
    db.query(AiAnalysisResult).delete()
    db.query(CandidateFormResponse).delete()
    db.query(Candidate).delete()
    db.query(JobPosting).delete()
    db.query(SchedulingPreference).delete()
    db.query(FormTemplate).delete()
    db.commit()


def _build_template(
    db: Session, recruiter: Recruiter, template_id: uuid.UUID, name: str
) -> FormTemplate:
    template = FormTemplate(
        template_id=template_id, recruiter_id=recruiter.recruiter_id, template_name=name
    )
    db.add(template)
    fields = [
        TemplateField(
            field_id=_id(f"{name}-full-name"),
            template_id=template_id,
            field_label="Full Name",
            field_type=FieldType.SHORT_TEXT,
            is_required=True,
            field_order=1,
        ),
        TemplateField(
            field_id=_id(f"{name}-email"),
            template_id=template_id,
            field_label="Email",
            field_type=FieldType.SHORT_TEXT,
            is_required=True,
            field_order=2,
        ),
        TemplateField(
            field_id=_id(f"{name}-experience"),
            template_id=template_id,
            field_label="Years of experience",
            field_type=FieldType.NUMBER,
            is_required=True,
            field_order=3,
        ),
    ]
    db.add_all(fields)
    return template


def _build_job(
    db: Session,
    recruiter: Recruiter,
    store: LocalResumeStore,
    job_id: uuid.UUID,
    template_id: uuid.UUID,
    job_title: str,
    **kw: object,
) -> JobPosting:
    store.create_job_folder(recruiter, job_id, job_title)
    job = JobPosting(
        job_id=job_id,
        recruiter_id=recruiter.recruiter_id,
        template_id=template_id,
        job_title=job_title,
        **kw,
    )
    db.add(job)
    return job


def main() -> None:
    _refuse_unless_local()
    db = SessionLocal()
    store = LocalResumeStore()
    try:
        _wipe(db)
        recruiter = seed_recruiter(db)
        db.flush()

        now = datetime.now(UTC)
        template_id = _id("template-standard")
        _build_template(db, recruiter, template_id, "Standard Role")
        db.flush()

        job_live = _build_job(
            db,
            recruiter,
            store,
            _id("job-live"),
            template_id,
            job_title="Backend Engineer",
            job_description="Own the API layer for a recruitment platform.",
            status=JobStatus.LIVE,
            is_accepting_responses=True,
            expires_at=now + timedelta(days=14),
            apply_slug="demo-live-backend",
        )
        job_closed = _build_job(
            db,
            recruiter,
            store,
            _id("job-closed"),
            template_id,
            job_title="QA Engineer",
            job_description="Closed, ready for processing.",
            status=JobStatus.CLOSED,
            is_accepting_responses=False,
            expires_at=now - timedelta(days=2),
            apply_slug="demo-closed-qa",
        )
        _build_job(
            db,
            recruiter,
            store,
            _id("job-paused"),
            template_id,
            job_title="Product Designer",
            job_description="Recruiter paused intake mid-campaign.",
            status=JobStatus.LIVE,
            is_accepting_responses=False,
            expires_at=now + timedelta(days=7),
            apply_slug="demo-paused-designer",
        )
        _build_job(
            db,
            recruiter,
            store,
            _id("job-draft"),
            template_id,
            job_title="Marketing Intern",
            job_description="Not launched yet.",
            status=JobStatus.DRAFT,
            is_accepting_responses=True,
            expires_at=now + timedelta(days=30),
            apply_slug="demo-draft-intern",
        )
        db.flush()

        name_field, email_field, exp_field = (
            _id("Standard Role-full-name"),
            _id("Standard Role-email"),
            _id("Standard Role-experience"),
        )

        candidates: list[Candidate] = []
        rank_counters: dict[uuid.UUID, int] = {}
        for i, resume_path in enumerate(_resume_files()):
            status = _ARCHETYPES[i % len(_ARCHETYPES)]
            job = job_closed if status == SubmissionStatus.REJECTED else job_live
            display_name = _display_name(resume_path)
            email = _email_for(display_name)
            ext = resume_path.suffix.lstrip(".").lower()
            content = resume_path.read_bytes()
            stored = store.store_resume(recruiter, job, f"{uuid.uuid4()}.{ext}", content)

            resume_text = None
            parse_error = None
            if status == SubmissionStatus.PARSE_ERROR:
                parse_error = "Scanned PDF had no extractable text layer and OCR fallback failed."
            else:
                try:
                    resume_text = extract_text(content, ext)
                except Exception as exc:  # a real dropped-in resume may genuinely fail to parse
                    parse_error = str(exc)
                    status = SubmissionStatus.PARSE_ERROR

            candidate = Candidate(
                candidate_id=_id(f"candidate-{i}"),
                job_id=job.job_id,
                full_name=display_name,
                email=email,
                submission_status=status,
                submitted_at=now - timedelta(hours=i + 1),
                parse_error=parse_error,
                resume_storage_key=stored.storage_key,
                resume_text=resume_text,
            )
            db.add(candidate)
            db.flush()
            db.add_all(
                [
                    CandidateFormResponse(
                        candidate_id=candidate.candidate_id,
                        field_id=name_field,
                        response_value=display_name,
                    ),
                    CandidateFormResponse(
                        candidate_id=candidate.candidate_id,
                        field_id=email_field,
                        response_value=email,
                    ),
                    CandidateFormResponse(
                        candidate_id=candidate.candidate_id, field_id=exp_field, response_value="3"
                    ),
                ]
            )

            if status in (SubmissionStatus.RANKED, SubmissionStatus.REJECTED):
                rank_position = rank_counters.get(job.job_id, 0) + 1
                rank_counters[job.job_id] = rank_position
                db.add(
                    AiAnalysisResult(
                        analysis_id=_id(f"analysis-{i}"),
                        candidate_id=candidate.candidate_id,
                        job_id=job.job_id,
                        semantic_score=max(0.05, 0.92 - rank_position * 0.15),
                        rank_position=rank_position,
                        matched_skills=_MATCHED,
                        missing_skills=_MISSING,
                        ai_feedback_summary="Strong match; light on infra experience."
                        if status == SubmissionStatus.RANKED
                        else "Below the bar for this posting.",
                    )
                )
            candidates.append(candidate)
        db.flush()

        ranked = [c for c in candidates if c.submission_status == SubmissionStatus.RANKED]
        rejected = [c for c in candidates if c.submission_status == SubmissionStatus.REJECTED]
        submitted = [c for c in candidates if c.submission_status == SubmissionStatus.SUBMITTED]

        if ranked:
            db.add(
                InterviewSlot(
                    slot_id=_id("slot-confirmed"),
                    candidate_id=ranked[0].candidate_id,
                    job_id=ranked[0].job_id,
                    recruiter_id=recruiter.recruiter_id,
                    scheduled_at=now + timedelta(days=2),
                    duration_minutes=30,
                    status=SlotStatus.CONFIRMED,
                    google_meet_link="https://meet.google.com/demo-confirmed",
                )
            )
            db.add(
                EmailLog(
                    email_id=_id("email-sent"),
                    recruiter_id=recruiter.recruiter_id,
                    candidate_id=ranked[0].candidate_id,
                    email_type=EmailType.INTERVIEW_INVITE,
                    subject=f"Interview invitation — {job_live.job_title}",
                    idempotency_key=_id("email-sent").hex,
                    delivery_status=DeliveryStatus.SENT,
                )
            )
        if len(ranked) > 1:
            db.add(
                InterviewSlot(
                    slot_id=_id("slot-cancelled"),
                    candidate_id=ranked[1].candidate_id,
                    job_id=ranked[1].job_id,
                    recruiter_id=recruiter.recruiter_id,
                    scheduled_at=now - timedelta(days=1),
                    duration_minutes=30,
                    status=SlotStatus.CANCELLED,
                    google_meet_link="https://meet.google.com/demo-cancelled",
                )
            )
        if submitted:
            db.add(
                InterviewSlot(
                    slot_id=_id("slot-pending"),
                    candidate_id=submitted[0].candidate_id,
                    job_id=submitted[0].job_id,
                    recruiter_id=recruiter.recruiter_id,
                    scheduled_at=now + timedelta(days=3),
                    duration_minutes=30,
                    status=SlotStatus.PENDING,
                    google_meet_link=None,
                )
            )
        if rejected:
            db.add(
                EmailLog(
                    email_id=_id("email-pending"),
                    recruiter_id=recruiter.recruiter_id,
                    candidate_id=rejected[0].candidate_id,
                    email_type=EmailType.REJECTION,
                    subject=f"Update on your application — {job_closed.job_title}",
                    idempotency_key=_id("email-pending").hex,
                    delivery_status=DeliveryStatus.PENDING,
                )
            )

        db.add(
            SchedulingPreference(
                preference_id=_id("scheduling-prefs"),
                recruiter_id=recruiter.recruiter_id,
                available_days=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
                available_start_time=time(9, 0),
                available_end_time=time(17, 0),
                slot_duration_minutes=30,
                timezone=settings.scheduling_timezone,
            )
        )

        db.add_all(
            [
                BackgroundTask(
                    task_id=_id("task-ranking"),
                    recruiter_id=recruiter.recruiter_id,
                    job_id=job_live.job_id,
                    task_type=TaskType.BATCH_RANKING,
                    status=TaskStatus.SUCCESS,
                    completed_at=now - timedelta(minutes=55),
                ),
                BackgroundTask(
                    task_id=_id("task-email-failed"),
                    recruiter_id=recruiter.recruiter_id,
                    job_id=job_closed.job_id,
                    task_type=TaskType.EMAIL_DISPATCH,
                    status=TaskStatus.FAILED,
                    error_message="Gmail API returned 429 after 3 retries.",
                    completed_at=now - timedelta(hours=2) + timedelta(seconds=30),
                ),
            ]
        )

        db.commit()
        print(f"recruiter_id: {recruiter.recruiter_id}")
        print(f"email: {recruiter.email}")
        print(f"jobs: {len(db.query(JobPosting).all())}  candidates: {len(candidates)}")
        print(f"apply (live): {settings.public_apply_base_url}/{job_live.apply_slug}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
