import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum

from app.core.db import Base
from app.schemas.enums import DeliveryStatus, EmailType


class EmailLog(Base):
    __tablename__ = "email_logs"
    # idempotency_key UNIQUE is a partial-free plain unique index, created via
    # op.create_index in the migration to match the naming convention used
    # elsewhere (uq_email_logs_idempotency_key) — it is the entire dedupe
    # mechanism (story AC); no application-level check duplicates it.

    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_slots.slot_id", ondelete="SET NULL"),
        nullable=True,
    )
    email_type: Mapped[EmailType] = mapped_column(
        Enum(EmailType, name="email_type_enum", native_enum=True), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_preview: Mapped[str | None] = mapped_column(Text(), nullable=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    # Set when the send is *attempted* (row insert), not when delivery
    # completes — stays NOT NULL for a PENDING row per docs/schema.md. A
    # PENDING row whose sent_at is old (vs. now) is a stalled attempt
    # (e.g. worker crashed between commit and send); the frontend can use
    # sent_at age + delivery_status == PENDING to distinguish "still
    # sending" from "stuck" without a new column.
    sent_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status_enum", native_enum=True), nullable=False
    )
    is_automated: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
