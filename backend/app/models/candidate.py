import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum

from app.core.db import Base
from app.schemas.enums import SubmissionStatus


class Candidate(Base):
    __tablename__ = "candidates"
    # UNIQUE (job_id, email) is a partial index (WHERE deleted_at IS NULL) —
    # created via op.create_index in the migration, not expressible as a plain
    # UniqueConstraint here, so it isn't declared in __table_args__.

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    resume_drive_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_drive_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resume_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submission_status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status_enum", native_enum=True),
        nullable=False,
        default=SubmissionStatus.SUBMITTED,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    parse_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    # docs/drift.md: ai_analysis_results (schema.md's designated home) doesn't
    # exist until US-18, so extracted text lives here until that table lands.
    resume_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    form_responses: Mapped[list["CandidateFormResponse"]] = relationship(
        cascade="all, delete-orphan"
    )


class CandidateFormResponse(Base):
    __tablename__ = "candidate_form_responses"
    __table_args__ = (
        UniqueConstraint("candidate_id", "field_id", name="uq_candidate_form_responses_field"),
    )

    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("template_fields.field_id"),
        nullable=False,
    )
    response_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
