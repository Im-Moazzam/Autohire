import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.template import FormTemplate
from app.schemas.enums import JobStatus


class JobPosting(Base):
    __tablename__ = "job_postings"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # No ondelete: templates are soft-deleted, and TEMPLATE_IN_USE guards
        # the path. A CASCADE here would silently destroy jobs.
        ForeignKey("form_templates.template_id"),
        nullable=False,
    )
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    job_description: Mapped[str] = mapped_column(Text(), nullable=False)
    jd_embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_form_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_form_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    google_drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apply_slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", native_enum=True),
        nullable=False,
        default=JobStatus.DRAFT,
    )
    is_accepting_responses: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    template: Mapped[FormTemplate] = relationship(viewonly=True)
