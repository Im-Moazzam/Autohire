import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import FieldType, SubmissionStatus


class FormResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: uuid.UUID
    field_label: str
    field_type: FieldType
    response_value: str | None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: uuid.UUID
    full_name: str
    email: str
    phone_number: str | None
    submission_status: SubmissionStatus
    submitted_at: datetime
    parse_error: str | None
    resume_url: str | None
    # What submission_status would be if this candidate had never been
    # rejected — derived from real data (an ai_analysis_results row, a
    # populated resume_text, a parse_error), never a guess. Only meaningful
    # when submission_status == REJECTED (that's the only state "undo"
    # applies to), but always present so the shape doesn't change per-row.
    restorable_status: SubmissionStatus


class RankedCandidateOut(CandidateOut):
    rank_position: int
    semantic_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    ai_feedback_summary: str | None


class CandidateDetailOut(CandidateOut):
    form_responses: list[FormResponseOut]


class CandidateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_status: SubmissionStatus
