import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.enums import FieldType

_OPTIONS_FIELD_TYPES = {FieldType.MULTIPLE_CHOICE, FieldType.DROPDOWN}


class TemplateFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: uuid.UUID
    field_label: str
    field_type: FieldType
    is_required: bool
    field_order: int
    options: list[str] | None = None


class TemplateFieldIn(BaseModel):
    """`field_id` present = keep this existing field row; absent = create a new
    one. Load-bearing: `candidate_form_responses.field_id` is an FK, so treating
    every save as delete-and-recreate would cascade away submitted responses."""

    field_id: uuid.UUID | None = None
    field_label: str
    field_type: FieldType
    is_required: bool = False
    field_order: int
    options: list[str] | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> "TemplateFieldIn":
        needs_options = self.field_type in _OPTIONS_FIELD_TYPES
        if needs_options and not self.options:
            raise ValueError(f"{self.field_type} fields require a non-empty options array")
        if not needs_options and self.options is not None:
            raise ValueError(f"{self.field_type} fields must not set options")
        return self


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: uuid.UUID
    template_name: str
    fields: list[TemplateFieldOut]
    created_at: datetime
    updated_at: datetime


class TemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_name: str
    fields: list[TemplateFieldIn] = Field(min_length=1)


class TemplateReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_name: str
    fields: list[TemplateFieldIn] = Field(min_length=1)
