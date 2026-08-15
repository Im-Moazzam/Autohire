from datetime import datetime

from pydantic import BaseModel

from app.schemas.template import TemplateFieldOut


class PublicJobOut(BaseModel):
    """Exposes only what a candidate needs. No recruiter identity, no job id,
    no counts — an unauthenticated caller has no business seeing any of that."""

    job_title: str
    job_description: str
    fields: list[TemplateFieldOut]
    is_accepting_responses: bool
    expires_at: datetime


class ApplySuccessOut(BaseModel):
    """No candidate_id: an internal UUID has no business reaching an
    unauthenticated caller, same reasoning as PublicJobOut."""

    submitted_at: datetime
    message: str
