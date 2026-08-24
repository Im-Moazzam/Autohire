import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import FormData

from app.adapters.base import ResumeStore
from app.adapters.resume_store import local_job_folder
from app.core.config import settings
from app.models.candidate import Candidate, CandidateFormResponse
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.models.template import TemplateField
from app.schemas.candidate import FormResponseOut
from app.schemas.common import PaginationParams
from app.schemas.enums import FieldType, SubmissionStatus
from app.services import job_service
from app.services.identity_fields import resolve_identity_fields
from app.services.resume_validation import EmptyFile, FileTooLarge, read_capped, sniff_extension

_MAX_RESPONSE_LEN = 5000

# Legal transition graph, closing docs/drift.md row 38. Mirrors
# job_service._LEGAL_TRANSITIONS. PARSED is never re-parsed — the retry AC
# ("retry only SUBMITTED and PARSE_ERROR") is itself a transition rule, not
# just a query filter. REJECTED is reachable from any non-terminal state.
_LEGAL_TRANSITIONS: dict[SubmissionStatus, set[SubmissionStatus]] = {
    SubmissionStatus.SUBMITTED: {
        SubmissionStatus.PARSED,
        SubmissionStatus.PARSE_ERROR,
        SubmissionStatus.REJECTED,
    },
    SubmissionStatus.PARSE_ERROR: {
        SubmissionStatus.PARSED,
        SubmissionStatus.PARSE_ERROR,
        SubmissionStatus.REJECTED,
    },
    SubmissionStatus.PARSED: {SubmissionStatus.RANKED, SubmissionStatus.REJECTED},
    SubmissionStatus.RANKED: {SubmissionStatus.INVITED, SubmissionStatus.REJECTED},
    SubmissionStatus.INVITED: {
        SubmissionStatus.CONFIRMED,
        SubmissionStatus.DECLINED,
        SubmissionStatus.RESCHEDULED,
        SubmissionStatus.REJECTED,
    },
    SubmissionStatus.RESCHEDULED: {
        SubmissionStatus.CONFIRMED,
        SubmissionStatus.DECLINED,
        SubmissionStatus.REJECTED,
    },
    SubmissionStatus.CONFIRMED: {SubmissionStatus.RESCHEDULED, SubmissionStatus.REJECTED},
    SubmissionStatus.DECLINED: set(),
    SubmissionStatus.REJECTED: set(),
}


def is_legal_transition(current: SubmissionStatus, target: SubmissionStatus) -> bool:
    if current == target:
        return True
    return target in _LEGAL_TRANSITIONS[current]


_UNKNOWN_FIELD = {"code": "UNKNOWN_FIELD", "message": "Submission contains an unrecognized field."}
_MISSING_REQUIRED = {"code": "MISSING_REQUIRED_FIELD", "message": "A required field is missing."}
_DUPLICATE_SUBMISSION = {
    "code": "DUPLICATE_SUBMISSION",
    "message": "An application with this email already exists for this job.",
}
_TEMPLATE_MISSING_IDENTITY = {
    "code": "TEMPLATE_MISSING_IDENTITY_FIELD",
    "message": "This job's template has no field recognizable as an email or full name.",
}


class _IdentityAnswers(BaseModel):
    """Length caps mirror the candidates columns (VARCHAR(150)/VARCHAR(255)).
    Real email validation, not a hand-rolled regex — same reasoning as
    Pydantic's own EmailStr, which needs the email-validator dependency."""

    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr


def _storage_failure_status_code() -> int:
    # Same local-vs-cloud distinction as job_service.finalize_launch: our own
    # filesystem failing is a 500, an upstream Drive failure is a 502.
    return 500 if settings.resume_store == "local" else 502


def _unknown_field(field_key: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={**_UNKNOWN_FIELD, "details": {"field_id": field_key}},
    )


def submit_application(
    db: Session,
    job: JobPosting,
    form: FormData,
    resume: UploadFile,
    store: ResumeStore,
) -> Candidate:
    """The public POST /apply/{slug} orchestration. Order matters and mirrors
    the story AC exactly: every check that can reject the submission runs
    before anything is stored, the resume is written before the candidate row
    is committed (never the reverse), and a storage failure leaves no row."""
    job_service.assert_job_accepting(job)  # -> JobNotAccepting, mapped to 410 by main.py

    fields_by_id = {field.field_id: field for field in job.template.fields}

    answers: dict[uuid.UUID, str] = {}
    for key, value in form.multi_items():
        if key == "resume":
            continue
        if not isinstance(value, str):
            raise _unknown_field(key)  # an unexpected second file part
        try:
            field_id = uuid.UUID(key)
        except ValueError as exc:
            raise _unknown_field(key) from exc
        if field_id not in fields_by_id:
            raise _unknown_field(key)
        answers[field_id] = value.strip()

    missing_required = [
        str(field.field_id)
        for field in fields_by_id.values()
        if field.is_required
        and field.field_type != FieldType.FILE_UPLOAD
        and not answers.get(field.field_id)
    ]
    if missing_required:
        raise HTTPException(
            status_code=422, detail={**_MISSING_REQUIRED, "details": {"missing": missing_required}}
        )

    too_long = [str(fid) for fid, value in answers.items() if len(value) > _MAX_RESPONSE_LEN]
    if too_long:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"A response exceeds {_MAX_RESPONSE_LEN} characters.",
                "details": {"fields": too_long},
            },
        )

    ordered_fields = list(fields_by_id.values())
    email_index, name_index = resolve_identity_fields([f.field_label for f in ordered_fields])
    if email_index is None or name_index is None:
        # Backstop only — template_service rejects a template missing either
        # field at save time. Reachable only for templates saved before that
        # guard existed.
        raise HTTPException(status_code=500, detail=_TEMPLATE_MISSING_IDENTITY)

    email_raw = answers.get(ordered_fields[email_index].field_id, "")
    name_raw = answers.get(ordered_fields[name_index].field_id, "")
    if not email_raw or not name_raw:
        # Identity fields are required regardless of their is_required flag —
        # a NULL here would violate the NOT NULL columns they feed.
        raise HTTPException(status_code=422, detail=_MISSING_REQUIRED)

    try:
        identity = _IdentityAnswers(full_name=name_raw, email=email_raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid submission data.",
                "details": {"errors": exc.errors()},
            },
        ) from exc

    existing = db.scalar(
        select(Candidate.candidate_id).where(
            Candidate.job_id == job.job_id,
            Candidate.email == identity.email,
            Candidate.deleted_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail=_DUPLICATE_SUBMISSION)

    try:
        content = read_capped(resume.file, settings.max_resume_mb * 1024 * 1024)
    except FileTooLarge as exc:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"Resume exceeds {settings.max_resume_mb}MB.",
            },
        ) from exc
    except EmptyFile as exc:
        raise HTTPException(
            status_code=422, detail={"code": "EMPTY_FILE", "message": "Resume file is empty."}
        ) from exc

    extension = sniff_extension(content)
    if extension is None:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "Only PDF and DOCX resumes are accepted.",
            },
        )

    recruiter = db.get(Recruiter, job.recruiter_id)
    assert recruiter is not None  # FK guarantees this

    # Server-generated name only — the candidate's raw filename never reaches
    # the filesystem or Drive (TC-08: path traversal / overwrite protection).
    stored_filename = f"{uuid.uuid4()}.{extension}"
    try:
        stored = store.store_resume(recruiter, job, stored_filename, content)
    except Exception as exc:
        raise HTTPException(
            status_code=_storage_failure_status_code(),
            detail={"code": "RESUME_UPLOAD_FAILED", "message": "Could not store the resume."},
        ) from exc

    candidate = Candidate(
        job_id=job.job_id,
        full_name=identity.full_name,
        email=identity.email,
        # Adapter-agnostic: a Drive upload returns a drive_file_id, a local
        # write doesn't — that distinguishes the store, not settings.app_env.
        resume_storage_key=stored.storage_key if stored.drive_file_id is None else None,
        resume_drive_file_id=stored.drive_file_id,
        resume_drive_url=stored.drive_url,
    )
    candidate.form_responses = [
        CandidateFormResponse(field_id=field_id, response_value=value)
        for field_id, value in answers.items()
    ]
    db.add(candidate)
    try:
        db.commit()
    except IntegrityError:
        # Race backstop behind the pre-check above: two concurrent
        # submissions for the same (job_id, email) both pass the SELECT, only
        # one wins the UNIQUE index.
        db.rollback()
        raise HTTPException(status_code=409, detail=_DUPLICATE_SUBMISSION) from None
    db.refresh(candidate)
    return candidate


def list_candidates(
    db: Session,
    job_id: uuid.UUID,
    params: PaginationParams,
    submission_status: SubmissionStatus | None,
    q: str | None,
) -> tuple[list[Candidate], int]:
    """Mirrors job_service.list_jobs: a COUNT over the filtered subquery, then
    one bounded page. Never touches candidate_form_responses or template_fields
    — CandidateOut carries no form_responses — so this stays 1 query
    regardless of page size (TC-10)."""
    base = select(Candidate).where(Candidate.job_id == job_id, Candidate.deleted_at.is_(None))
    if submission_status is not None:
        # Hits ix_candidates_job_status (job_id, submission_status).
        base = base.where(Candidate.submission_status == submission_status)
    if q:
        base = base.where(or_(Candidate.full_name.ilike(f"%{q}%"), Candidate.email.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(Candidate.submitted_at.desc(), Candidate.candidate_id.desc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return list(rows), total


def get_owned_candidate(
    db: Session, recruiter_id: uuid.UUID, candidate_id: uuid.UUID
) -> Candidate | None:
    """The only ownership path for candidates — scoped through the owning job's
    recruiter_id in one query, never a two-step lookup. Cross-tenant, deleted
    candidate, or deleted job all resolve to None here (ADR-004 P8: 404, not 403)."""
    return db.scalar(
        select(Candidate)
        .join(JobPosting, JobPosting.job_id == Candidate.job_id)
        .where(
            Candidate.candidate_id == candidate_id,
            Candidate.deleted_at.is_(None),
            JobPosting.recruiter_id == recruiter_id,
            JobPosting.deleted_at.is_(None),
        )
    )


def form_responses(db: Session, candidate_id: uuid.UUID) -> list[FormResponseOut]:
    """One query, joined to template_fields for the label — never stored on
    the response row (AC), and never a per-response lookup (TC-10)."""
    rows = db.execute(
        select(CandidateFormResponse, TemplateField)
        .join(TemplateField, TemplateField.field_id == CandidateFormResponse.field_id)
        .where(CandidateFormResponse.candidate_id == candidate_id)
        .order_by(TemplateField.field_order)
    ).all()
    return [
        FormResponseOut(
            field_id=field.field_id,
            field_label=field.field_label,
            field_type=field.field_type,
            response_value=response.response_value,
        )
        for response, field in rows
    ]


def resume_url_for(candidate: Candidate) -> str | None:
    """Computed, never a column (docs/schema.md). Branches on the candidate's
    own stored fields, not settings.resume_store — a local write never sets
    resume_drive_url, a Drive upload never sets resume_storage_key (TS-07)."""
    if candidate.resume_storage_key:
        return f"/api/v1/candidates/{candidate.candidate_id}/resume"
    return candidate.resume_drive_url


def resolve_resume_path(candidate: Candidate) -> Path | None:
    """Resolves resume_storage_key for streaming. Only ever set for a local
    write (candidate_service.submit_application only populates it when the
    store's StoredFile has no drive_file_id, TS-07), so a Drive-backed
    candidate always returns None here and the route 404s, matching
    resume_url_for's local-only route. Returns None (never raises) for: no
    key stored, file missing, or the resolved path escaping the job's
    folder — the route maps all three to 404 uniformly."""
    if not candidate.resume_storage_key:
        return None
    folder = local_job_folder(candidate.job_id).resolve()
    target = Path(candidate.resume_storage_key).resolve()
    if folder not in target.parents:
        return None
    if not target.is_file():
        return None
    return target
