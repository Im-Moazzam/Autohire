"""All Phase 1 stub data, in one module (TS-02). Every route reads from here so
stub removal is mechanical: delete the fixture, delete the # STUB comment, wire
up the real query. Nothing here is ever an empty list — see docs/checklists/ux.md,
every list/detail/failure state must be reachable through a real request."""

import uuid
from datetime import UTC, datetime, timedelta

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


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"autohire.fixture/{name}")


NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)

# --- Templates ---------------------------------------------------------

TEMPLATE_1_ID = _id("template-1")
TEMPLATE_2_ID = _id("template-2")

FIELD_NAME_ID = _id("field-full-name")
FIELD_EXPERIENCE_ID = _id("field-experience")
FIELD_LEVEL_ID = _id("field-level")

TEMPLATES: dict[uuid.UUID, dict] = {
    TEMPLATE_1_ID: {
        "template_id": TEMPLATE_1_ID,
        "template_name": "Standard Software Role",
        "fields": [
            {
                "field_id": FIELD_NAME_ID,
                "field_label": "Years of experience",
                "field_type": FieldType.NUMBER,
                "is_required": True,
                "field_order": 1,
                "options": None,
            },
            {
                "field_id": FIELD_EXPERIENCE_ID,
                "field_label": "Why this role?",
                "field_type": FieldType.PARAGRAPH,
                "is_required": True,
                "field_order": 2,
                "options": None,
            },
            {
                "field_id": FIELD_LEVEL_ID,
                "field_label": "Preferred seniority",
                "field_type": FieldType.DROPDOWN,
                "is_required": False,
                "field_order": 3,
                "options": ["Junior", "Mid", "Senior"],
            },
        ],
        "created_at": NOW - timedelta(days=10),
        "updated_at": NOW - timedelta(days=2),
    },
    TEMPLATE_2_ID: {
        "template_id": TEMPLATE_2_ID,
        "template_name": "Internship",
        "fields": [
            {
                "field_id": _id("field-university"),
                "field_label": "University",
                "field_type": FieldType.SHORT_TEXT,
                "is_required": True,
                "field_order": 1,
                "options": None,
            },
        ],
        "created_at": NOW - timedelta(days=5),
        "updated_at": NOW - timedelta(days=5),
    },
}

# --- Jobs ----------------------------------------------------------------

JOB_LIVE_ID = _id("job-live")
JOB_EXPIRED_ID = _id("job-expired")
JOB_PAUSED_ID = _id("job-paused")
JOB_DRAFT_ID = _id("job-draft")
JOB_CLOSED_ID = _id("job-closed")

JOBS: dict[uuid.UUID, dict] = {
    JOB_LIVE_ID: {
        "job_id": JOB_LIVE_ID,
        "job_title": "Backend Engineer",
        "job_description": "Own the API layer for a recruitment platform.",
        "template_id": TEMPLATE_1_ID,
        "status": JobStatus.LIVE,
        "is_accepting_responses": True,
        "expires_at": NOW + timedelta(days=14),
        "apply_slug": "live-slug",
        "google_drive_folder_id": None,
        "created_at": NOW - timedelta(days=3),
        "updated_at": NOW - timedelta(days=1),
    },
    JOB_EXPIRED_ID: {
        "job_id": JOB_EXPIRED_ID,
        "job_title": "Data Analyst",
        "job_description": "Applications closed by TTL.",
        "template_id": TEMPLATE_1_ID,
        "status": JobStatus.LIVE,
        "is_accepting_responses": True,
        "expires_at": NOW - timedelta(days=1),
        "apply_slug": "expired-slug",
        "google_drive_folder_id": None,
        "created_at": NOW - timedelta(days=30),
        "updated_at": NOW - timedelta(days=30),
    },
    JOB_PAUSED_ID: {
        "job_id": JOB_PAUSED_ID,
        "job_title": "Product Designer",
        "job_description": "Recruiter paused intake mid-campaign.",
        "template_id": TEMPLATE_1_ID,
        "status": JobStatus.LIVE,
        "is_accepting_responses": False,
        "expires_at": NOW + timedelta(days=7),
        "apply_slug": "paused-slug",
        "google_drive_folder_id": None,
        "created_at": NOW - timedelta(days=6),
        "updated_at": NOW - timedelta(hours=2),
    },
    JOB_DRAFT_ID: {
        "job_id": JOB_DRAFT_ID,
        "job_title": "Marketing Intern",
        "job_description": "Not launched yet.",
        "template_id": TEMPLATE_2_ID,
        "status": JobStatus.DRAFT,
        "is_accepting_responses": True,
        "expires_at": NOW + timedelta(days=30),
        "apply_slug": "draft-slug",
        "google_drive_folder_id": None,
        "created_at": NOW - timedelta(hours=1),
        "updated_at": NOW - timedelta(hours=1),
    },
    JOB_CLOSED_ID: {
        "job_id": JOB_CLOSED_ID,
        "job_title": "QA Engineer",
        "job_description": "Closed, ready for processing.",
        "template_id": TEMPLATE_1_ID,
        "status": JobStatus.CLOSED,
        "is_accepting_responses": False,
        "expires_at": NOW - timedelta(days=2),
        "apply_slug": "closed-slug",
        "google_drive_folder_id": "fixture-drive-folder",
        "created_at": NOW - timedelta(days=20),
        "updated_at": NOW - timedelta(days=2),
    },
}

# Legal transition graph, ADR-004 P3 / docs/api-contract.md § Jobs
_LEGAL_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DRAFT: {JobStatus.LIVE},
    JobStatus.LIVE: {JobStatus.CLOSED},
    JobStatus.CLOSED: {JobStatus.PROCESSED},
    JobStatus.PROCESSED: set(),
}


def is_legal_job_transition(current: JobStatus, target: JobStatus) -> bool:
    if current == target:
        return True
    return target in _LEGAL_TRANSITIONS[current]


# --- Candidates ------------------------------------------------------------

CANDIDATE_SUBMITTED_ID = _id("candidate-submitted")
CANDIDATE_PARSED_ID = _id("candidate-parsed")
CANDIDATE_RANKED_1_ID = _id("candidate-ranked-1")
CANDIDATE_RANKED_2_ID = _id("candidate-ranked-2")
CANDIDATE_PARSE_ERROR_ID = _id("candidate-parse-error")
CANDIDATE_REJECTED_ID = _id("candidate-rejected")

CANDIDATES: dict[uuid.UUID, dict] = {
    CANDIDATE_SUBMITTED_ID: {
        "candidate_id": CANDIDATE_SUBMITTED_ID,
        "job_id": JOB_LIVE_ID,
        "full_name": "Amina Tariq",
        "email": "amina.tariq@example.com",
        "phone_number": "+92-300-1112222",
        "submission_status": SubmissionStatus.SUBMITTED,
        "submitted_at": NOW - timedelta(hours=3),
        "parse_error": None,
        "resume_storage_key": "resumes/amina-tariq.pdf",
        "resume_drive_url": None,
        "rank_position": None,
        "semantic_score": None,
        "matched_skills": [],
        "missing_skills": [],
        "ai_feedback_summary": None,
        "form_responses": [
            {"field_id": FIELD_NAME_ID, "response_value": "3"},
            {"field_id": FIELD_EXPERIENCE_ID, "response_value": "Excited about the API work."},
        ],
    },
    CANDIDATE_PARSED_ID: {
        "candidate_id": CANDIDATE_PARSED_ID,
        "job_id": JOB_LIVE_ID,
        "full_name": "Hassan Raza",
        "email": "hassan.raza@example.com",
        "phone_number": None,
        "submission_status": SubmissionStatus.PARSED,
        "submitted_at": NOW - timedelta(hours=5),
        "parse_error": None,
        "resume_storage_key": "resumes/hassan-raza.pdf",
        "resume_drive_url": None,
        "rank_position": None,
        "semantic_score": None,
        "matched_skills": [],
        "missing_skills": [],
        "ai_feedback_summary": None,
        "form_responses": [
            {"field_id": FIELD_NAME_ID, "response_value": "5"},
            {"field_id": FIELD_EXPERIENCE_ID, "response_value": "Backend-heavy background."},
        ],
    },
    CANDIDATE_RANKED_1_ID: {
        "candidate_id": CANDIDATE_RANKED_1_ID,
        "job_id": JOB_LIVE_ID,
        "full_name": "Sara Khan",
        "email": "sara.khan@example.com",
        "phone_number": "+92-300-3334444",
        "submission_status": SubmissionStatus.RANKED,
        "submitted_at": NOW - timedelta(days=1),
        "parse_error": None,
        "resume_storage_key": "resumes/sara-khan.pdf",
        "resume_drive_url": None,
        "rank_position": 1,
        "semantic_score": 0.92,
        "matched_skills": ["FastAPI", "PostgreSQL", "SQLAlchemy"],
        "missing_skills": ["Kubernetes"],
        "ai_feedback_summary": "Strong backend match; light on infra experience.",
        "form_responses": [
            {"field_id": FIELD_NAME_ID, "response_value": "6"},
            {"field_id": FIELD_EXPERIENCE_ID, "response_value": "Led a 3-person backend team."},
            {"field_id": FIELD_LEVEL_ID, "response_value": "Senior"},
        ],
    },
    CANDIDATE_RANKED_2_ID: {
        "candidate_id": CANDIDATE_RANKED_2_ID,
        "job_id": JOB_LIVE_ID,
        "full_name": "Bilal Ahmed",
        "email": "bilal.ahmed@example.com",
        "phone_number": None,
        "submission_status": SubmissionStatus.RANKED,
        "submitted_at": NOW - timedelta(days=1, hours=4),
        "parse_error": None,
        "resume_storage_key": "resumes/bilal-ahmed.pdf",
        "resume_drive_url": None,
        "rank_position": 2,
        "semantic_score": 0.81,
        "matched_skills": ["Python", "REST APIs"],
        "missing_skills": ["PostgreSQL", "SQLAlchemy"],
        "ai_feedback_summary": "Solid generalist, less database depth than top match.",
        "form_responses": [
            {"field_id": FIELD_NAME_ID, "response_value": "4"},
            {"field_id": FIELD_EXPERIENCE_ID, "response_value": "Full-stack generalist."},
            {"field_id": FIELD_LEVEL_ID, "response_value": "Mid"},
        ],
    },
    CANDIDATE_PARSE_ERROR_ID: {
        "candidate_id": CANDIDATE_PARSE_ERROR_ID,
        "job_id": JOB_LIVE_ID,
        "full_name": "Usman Ali",
        "email": "usman.ali@example.com",
        "phone_number": None,
        "submission_status": SubmissionStatus.PARSE_ERROR,
        "submitted_at": NOW - timedelta(hours=6),
        "parse_error": "Scanned PDF had no extractable text layer and OCR fallback failed.",
        "resume_storage_key": "resumes/usman-ali.pdf",
        "resume_drive_url": None,
        "rank_position": None,
        "semantic_score": None,
        "matched_skills": [],
        "missing_skills": [],
        "ai_feedback_summary": None,
        "form_responses": [
            {"field_id": FIELD_NAME_ID, "response_value": "2"},
            {"field_id": FIELD_EXPERIENCE_ID, "response_value": "n/a"},
        ],
    },
    CANDIDATE_REJECTED_ID: {
        "candidate_id": CANDIDATE_REJECTED_ID,
        "job_id": JOB_CLOSED_ID,
        "full_name": "Zara Iqbal",
        "email": "zara.iqbal@example.com",
        "phone_number": None,
        "submission_status": SubmissionStatus.REJECTED,
        "submitted_at": NOW - timedelta(days=15),
        "parse_error": None,
        "resume_storage_key": "resumes/zara-iqbal.pdf",
        "resume_drive_url": None,
        "rank_position": 3,
        "semantic_score": 0.44,
        "matched_skills": [],
        "missing_skills": ["Python", "SQL"],
        "ai_feedback_summary": "Below the bar for this posting.",
        "form_responses": [
            {"field_id": FIELD_NAME_ID, "response_value": "1"},
            {"field_id": FIELD_EXPERIENCE_ID, "response_value": "Recent graduate."},
        ],
    },
}


def candidates_for_job(job_id: uuid.UUID) -> list[dict]:
    return [c for c in CANDIDATES.values() if c["job_id"] == job_id]


def resume_url_for(candidate: dict) -> str | None:
    """Computed, never a column — mirrors docs/schema.md's note under `candidates`."""
    from app.core.config import settings

    if settings.app_env == "local":
        return (
            f"/local-storage/{candidate['resume_storage_key']}"
            if candidate["resume_storage_key"]
            else None
        )
    return candidate["resume_drive_url"]


def form_responses_for(candidate: dict) -> list[dict]:
    field_by_id = {
        field["field_id"]: field for template in TEMPLATES.values() for field in template["fields"]
    }
    out = []
    for response in candidate["form_responses"]:
        field = field_by_id[response["field_id"]]
        out.append(
            {
                "field_id": field["field_id"],
                "field_label": field["field_label"],
                "field_type": field["field_type"],
                "response_value": response["response_value"],
            }
        )
    return out


# --- Tasks -------------------------------------------------------------

TASK_RUNNING_ID = _id("task-running")
TASK_SUCCESS_ID = _id("task-success")
TASK_FAILED_ID = _id("task-failed")

TASKS: dict[uuid.UUID, dict] = {
    TASK_RUNNING_ID: {
        "task_id": TASK_RUNNING_ID,
        "task_type": TaskType.BATCH_RANKING,
        "status": TaskStatus.RUNNING,
        "started_at": NOW - timedelta(minutes=2),
        "completed_at": None,
        "error_message": None,
    },
    TASK_SUCCESS_ID: {
        "task_id": TASK_SUCCESS_ID,
        "task_type": TaskType.RESUME_PARSE,
        "status": TaskStatus.SUCCESS,
        "started_at": NOW - timedelta(hours=1),
        "completed_at": NOW - timedelta(minutes=55),
        "error_message": None,
    },
    TASK_FAILED_ID: {
        "task_id": TASK_FAILED_ID,
        "task_type": TaskType.EMAIL_DISPATCH,
        "status": TaskStatus.FAILED,
        "started_at": NOW - timedelta(hours=2),
        "completed_at": NOW - timedelta(hours=2) + timedelta(seconds=30),
        "error_message": "Gmail API returned 429 after 3 retries.",
    },
}

PROCESS_STATUS_BY_JOB: dict[uuid.UUID, dict] = {
    JOB_CLOSED_ID: {
        "status": TaskStatus.SUCCESS,
        "total": 1,
        "processed": 1,
        "failed": 0,
        "error_message": None,
    },
    JOB_LIVE_ID: {
        "status": TaskStatus.RUNNING,
        "total": 5,
        "processed": 4,
        "failed": 1,
        "error_message": None,
    },
}

# --- Scheduling ----------------------------------------------------------
# preferences are real as of US-24 (scheduling_service); the fixtures below
# still back the /available-slots stub (US-26).

AVAILABLE_SLOTS: list[dict] = [
    {
        "starts_at": NOW + timedelta(days=1, hours=1),
        "ends_at": NOW + timedelta(days=1, hours=1, minutes=30),
    },
    {
        "starts_at": NOW + timedelta(days=1, hours=2),
        "ends_at": NOW + timedelta(days=1, hours=2, minutes=30),
    },
    {
        "starts_at": NOW + timedelta(days=2, hours=1),
        "ends_at": NOW + timedelta(days=2, hours=1, minutes=30),
    },
]

SLOT_CONFIRMED_ID = _id("slot-confirmed")
SLOT_CANCELLED_ID = _id("slot-cancelled")
SLOT_PENDING_ID = _id("slot-pending")

INTERVIEW_SLOTS: dict[uuid.UUID, dict] = {
    SLOT_CONFIRMED_ID: {
        "slot_id": SLOT_CONFIRMED_ID,
        "candidate_id": CANDIDATE_RANKED_1_ID,
        "job_id": JOB_LIVE_ID,
        "scheduled_at": NOW + timedelta(days=2, hours=3),
        "duration_minutes": 30,
        "status": SlotStatus.CONFIRMED,
        "google_meet_link": "https://meet.google.com/fixture-confirmed",
    },
    SLOT_CANCELLED_ID: {
        "slot_id": SLOT_CANCELLED_ID,
        "candidate_id": CANDIDATE_RANKED_2_ID,
        "job_id": JOB_LIVE_ID,
        "scheduled_at": NOW - timedelta(days=1),
        "duration_minutes": 30,
        "status": SlotStatus.CANCELLED,
        "google_meet_link": "https://meet.google.com/fixture-cancelled",
    },
    SLOT_PENDING_ID: {
        "slot_id": SLOT_PENDING_ID,
        "candidate_id": CANDIDATE_SUBMITTED_ID,
        "job_id": JOB_LIVE_ID,
        "scheduled_at": NOW + timedelta(days=3),
        "duration_minutes": 30,
        "status": SlotStatus.PENDING,
        "google_meet_link": None,
    },
}


def candidate_name(candidate_id: uuid.UUID) -> str:
    return CANDIDATES[candidate_id]["full_name"]


# --- Email logs --------------------------------------------------------

EMAIL_SENT_ID = _id("email-sent")
EMAIL_FAILED_ID = _id("email-failed")
EMAIL_PENDING_ID = _id("email-pending")

EMAIL_LOGS: dict[uuid.UUID, dict] = {
    EMAIL_SENT_ID: {
        "email_id": EMAIL_SENT_ID,
        "job_id": JOB_LIVE_ID,
        "candidate_id": CANDIDATE_RANKED_1_ID,
        "email_type": EmailType.INTERVIEW_INVITE,
        "subject": "Interview invitation — Backend Engineer",
        "body_preview": "We'd like to invite you to interview...",
        "delivery_status": DeliveryStatus.SENT,
        "sent_at": NOW - timedelta(days=1),
        "is_automated": True,
    },
    EMAIL_FAILED_ID: {
        "email_id": EMAIL_FAILED_ID,
        "job_id": JOB_LIVE_ID,
        "candidate_id": CANDIDATE_RANKED_2_ID,
        "email_type": EmailType.CANCELLATION,
        "subject": "Interview cancelled — Backend Engineer",
        "body_preview": None,
        "delivery_status": DeliveryStatus.FAILED,
        "sent_at": NOW - timedelta(hours=12),
        "is_automated": True,
    },
    EMAIL_PENDING_ID: {
        "email_id": EMAIL_PENDING_ID,
        "job_id": JOB_CLOSED_ID,
        "candidate_id": CANDIDATE_REJECTED_ID,
        "email_type": EmailType.REJECTION,
        "subject": "Update on your application — QA Engineer",
        "body_preview": None,
        "delivery_status": DeliveryStatus.PENDING,
        "sent_at": NOW - timedelta(minutes=5),
        "is_automated": True,
    },
}
