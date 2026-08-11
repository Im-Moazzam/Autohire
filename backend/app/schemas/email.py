import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.enums import DeliveryStatus, EmailType


class EmailLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    email_type: EmailType
    subject: str
    body_preview: str | None
    delivery_status: DeliveryStatus
    sent_at: datetime
    is_automated: bool


class EmailSendIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_type: EmailType
    candidate_ids: list[uuid.UUID]
    subject: str | None = None
    body: str | None = None
