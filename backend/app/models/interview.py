import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum

from app.core.db import Base
from app.schemas.enums import SlotStatus


class InterviewSlot(Base):
    __tablename__ = "interview_slots"
    # Two partial UNIQUE indexes, created via op.create_index in the migration
    # (WHERE status IN ('PENDING','CONFIRMED')), not expressible as a plain
    # UniqueConstraint here: uq_interview_slots_candidate_live (one live slot
    # per candidate) and uq_interview_slots_recruiter_time (concurrency
    # backstop for exact-timestamp double-booking; the real overlap check is
    # the interval check in interview_service.generate_slots).

    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer(), nullable=False)
    google_calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_meet_link: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, name="slot_status_enum", native_enum=True),
        nullable=False,
        default=SlotStatus.PENDING,
    )
    # Phase 2 (candidate replies / reschedule flow, out of scope here).
    # intent_detected is omitted entirely — it needs an intent_enum only
    # Phase 2 defines (docs/drift.md).
    candidate_reply_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    reschedule_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
