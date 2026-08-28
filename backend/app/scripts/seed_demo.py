"""Rebuilds a minimal demo world for local manual/frontend testing: a
recruiter, one template, a single live job ("Backend Engineer"), and every
resume dropped in backend/seed_resumes/ (falling back to the bundled test
fixture) applied to it, all freshly submitted.

    mise run db:seed-demo

Wipes and rebuilds every run (deterministic uuid5 IDs), so it's safe to
re-run after `mise run reset`. Never run this against anything but a local
dev database - see _refuse_unless_local below.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
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
from app.schemas.enums import FieldType, JobStatus, SubmissionStatus
from app.scripts.seed import _FAKE_USERINFO, _refuse_unless_local, seed_recruiter

SEED_RESUMES_DIR = Path(__file__).resolve().parents[2] / "seed_resumes"
FALLBACK_RESUME = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "resumes" / "Moazzam_Resume.pdf"
)


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


_ME_SENTINEL = "@me"


def _most_recently_logged_in(db: Session) -> Recruiter:
    """Excludes the synthetic seed.py identity - only a recruiter who has
    actually completed real Google OAuth counts as "me" for a live demo."""
    recruiter = (
        db.query(Recruiter)
        .filter(Recruiter.google_user_id != _FAKE_USERINFO.sub)
        .order_by(Recruiter.last_login_at.desc().nullslast())
        .first()
    )
    if recruiter is None:
        raise SystemExit(
            "SEED_DEMO_EMAIL=@me: no real recruiter has logged in yet (excluding the "
            "synthetic seed.py identity) - log in via Google OAuth first."
        )
    return recruiter


def _target_recruiter(db: Session) -> Recruiter:
    """SEED_DEMO_EMAIL attaches the demo world to a recruiter who already
    signed in via real Google OAuth, instead of the synthetic seed.py
    identity - useful when testing against your own logged-in session, or
    live-demoing the flow end to end. SEED_DEMO_EMAIL=@me auto-targets
    whoever most recently logged in, so a demo needs no email typed at all:
    log in fresh, then run `mise run db:seed-demo-me`."""
    email = os.getenv("SEED_DEMO_EMAIL")
    if not email:
        return seed_recruiter(db)
    if email == _ME_SENTINEL:
        return _most_recently_logged_in(db)
    recruiter = db.query(Recruiter).filter_by(email=email).one_or_none()
    if recruiter is None:
        raise SystemExit(f"SEED_DEMO_EMAIL={email!r}: no recruiter with that email exists yet")
    return recruiter


def main() -> None:
    _refuse_unless_local()
    db = SessionLocal()
    store = LocalResumeStore()
    try:
        _wipe(db)
        recruiter = _target_recruiter(db)
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
        db.flush()

        name_field, email_field, exp_field = (
            _id("Standard Role-full-name"),
            _id("Standard Role-email"),
            _id("Standard Role-experience"),
        )

        candidates: list[Candidate] = []
        for i, resume_path in enumerate(_resume_files()):
            display_name = _display_name(resume_path)
            email = _email_for(display_name)
            ext = resume_path.suffix.lstrip(".").lower()
            content = resume_path.read_bytes()
            stored = store.store_resume(recruiter, job_live, f"{uuid.uuid4()}.{ext}", content)

            candidate = Candidate(
                candidate_id=_id(f"candidate-{i}"),
                job_id=job_live.job_id,
                full_name=display_name,
                email=email,
                submission_status=SubmissionStatus.SUBMITTED,
                submitted_at=now - timedelta(hours=i + 1),
                resume_storage_key=stored.storage_key,
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
            candidates.append(candidate)
        db.flush()

        db.commit()
        print(f"recruiter_id: {recruiter.recruiter_id}")
        print(f"email: {recruiter.email}")
        print(f"jobs: {len(db.query(JobPosting).all())}  candidates: {len(candidates)}")
        print(f"apply (live): {settings.public_apply_base_url}/{job_live.apply_slug}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
