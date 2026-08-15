import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.schemas.enums import FieldType


class FormTemplate(Base):
    __tablename__ = "form_templates"

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recruiter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recruiters.recruiter_id", ondelete="CASCADE"),
        nullable=False,
    )
    template_name: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    fields: Mapped[list["TemplateField"]] = relationship(
        back_populates="template",
        order_by="TemplateField.field_order",
        cascade="all, delete-orphan",
    )


class TemplateField(Base):
    __tablename__ = "template_fields"
    __table_args__ = (
        UniqueConstraint("template_id", "field_order", name="uq_template_fields_order"),
    )

    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("form_templates.template_id", ondelete="CASCADE"),
        nullable=False,
    )
    field_label: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[FieldType] = mapped_column(
        Enum(FieldType, name="field_type_enum", native_enum=True), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    field_order: Mapped[int] = mapped_column(Integer(), nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSONB(), nullable=True)

    template: Mapped[FormTemplate] = relationship(back_populates="fields")
