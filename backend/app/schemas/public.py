from datetime import datetime

from pydantic import BaseModel

from app.schemas.template import TemplateFieldOut


class PublicJobOut(BaseModel):
    """Exposes only what a candidate needs. No recruiter identity, no job id,
    no counts — an unauthenticated caller has no business seeing any of that.

    `fields` carries `TemplateFieldOut.field_id` (a UUID) and that is
    deliberate, not an oversight: `candidate_form_responses.field_id` is an
    FK, so US-12's submission payload must key answers by field_id — there is
    no other stable identifier (labels aren't unique, positions shift when a
    recruiter edits the template). It identifies a form field, not a
    recruiter, job, or tenant, and it isn't enumerable without the slug."""

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
