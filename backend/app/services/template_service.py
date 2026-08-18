import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.template import FormTemplate, TemplateField
from app.schemas.common import PaginationParams
from app.schemas.template import TemplateFieldIn
from app.services.identity_fields import resolve_identity_fields

_DUPLICATE_NAME = {
    "code": "DUPLICATE_TEMPLATE_NAME",
    "message": "A template with this name already exists.",
}
_WRITE_FAILED = {
    "code": "TEMPLATE_WRITE_FAILED",
    "message": "The template could not be saved.",
}
_TEMPLATE_IN_USE = {
    "code": "TEMPLATE_IN_USE",
    "message": "This template is referenced by a job posting.",
}


def _assert_has_identity_fields(fields: list[TemplateFieldIn]) -> None:
    """A candidate applying through this template must resolve an email and a
    full name (US-12 needs both to write a candidates row). Checked here, at
    save time, so a missing field is the recruiter's 422 to fix in the
    template builder — not a candidate's 500 mid-application."""
    email_index, name_index = resolve_identity_fields([field.field_label for field in fields])
    missing = [
        column
        for column, index in (("email", email_index), ("full_name", name_index))
        if index is None
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TEMPLATE_MISSING_IDENTITY_FIELD",
                "message": "Template must have a field recognizable as an email and a full name.",
                "details": {"missing": missing},
            },
        )


def _commit(db: Session, template: FormTemplate) -> None:
    """A bad field must leave no template row behind: any DB-level failure
    (unique violation, or e.g. a label too long for VARCHAR(200)) rolls the
    whole transaction back, so the template insert doesn't survive either —
    and rolls the session back cleanly so the next request on it isn't
    poisoned by a dangling failed transaction."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_NAME) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=_WRITE_FAILED
        ) from None
    db.refresh(template)


def _normalize_order(fields: list[TemplateFieldIn]) -> list[TemplateFieldIn]:
    """Reassign field_order to 0..n-1 by the client's ascending order, so any
    ascending sequence the client sends (e.g. [5, 10, 20]) is accepted without
    tripping the (template_id, field_order) UNIQUE constraint."""
    ordered = sorted(fields, key=lambda f: f.field_order)
    for index, field in enumerate(ordered):
        field.field_order = index
    return ordered


def list_templates(
    db: Session, recruiter_id: uuid.UUID, params: PaginationParams
) -> tuple[list[FormTemplate], int]:
    base = select(FormTemplate).where(
        FormTemplate.recruiter_id == recruiter_id, FormTemplate.deleted_at.is_(None)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (
        db.scalars(
            base.options(selectinload(FormTemplate.fields))
            .order_by(FormTemplate.created_at)
            .offset((params.page - 1) * params.size)
            .limit(params.size)
        )
        .unique()
        .all()
    )
    return list(rows), total


def get_template(
    db: Session, recruiter_id: uuid.UUID, template_id: uuid.UUID
) -> FormTemplate | None:
    return db.scalar(
        select(FormTemplate)
        .where(
            FormTemplate.template_id == template_id,
            FormTemplate.recruiter_id == recruiter_id,
            FormTemplate.deleted_at.is_(None),
        )
        .options(selectinload(FormTemplate.fields))
    )


def create_template(
    db: Session, recruiter_id: uuid.UUID, template_name: str, fields: list[TemplateFieldIn]
) -> FormTemplate:
    _assert_has_identity_fields(fields)
    template = FormTemplate(recruiter_id=recruiter_id, template_name=template_name)
    for field in _normalize_order(fields):
        template.fields.append(
            TemplateField(
                field_label=field.field_label,
                field_type=field.field_type,
                is_required=field.is_required,
                field_order=field.field_order,
                options=field.options,
            )
        )
    db.add(template)
    _commit(db, template)
    return template


def replace_template(
    db: Session, template: FormTemplate, template_name: str, fields: list[TemplateFieldIn]
) -> FormTemplate:
    """Reconciles by field_id: a field with an id keeps its row (its answers on
    candidate_form_responses stay valid), a field without one is a new row, and
    any existing row not present in the payload is deleted."""
    _assert_has_identity_fields(fields)
    template.template_name = template_name
    template.updated_at = datetime.now(UTC)

    sent_ids = {field.field_id for field in fields if field.field_id is not None}
    existing_by_id = {field.field_id: field for field in template.fields}
    for existing_id, existing_field in list(existing_by_id.items()):
        if existing_id not in sent_ids:
            template.fields.remove(existing_field)

    db.flush()  # clear removed rows before renumbering, or the unique constraint trips

    ordered_fields = _normalize_order(fields)

    # (template_id, field_order) is a non-deferred UNIQUE constraint, so
    # reassigning a kept row straight to its final order can collide with
    # another kept row that hasn't moved yet. Bump every kept row out of the
    # target range first, then assign final orders in a second pass.
    kept_rows = [
        (field, existing_by_id[field.field_id])
        for field in ordered_fields
        if field.field_id is not None and field.field_id in existing_by_id
    ]
    for offset, (_field, row) in enumerate(kept_rows):
        row.field_order = len(fields) + offset
    db.flush()

    for field in ordered_fields:
        if field.field_id is not None and field.field_id in existing_by_id:
            row = existing_by_id[field.field_id]
            row.field_label = field.field_label
            row.field_type = field.field_type
            row.is_required = field.is_required
            row.field_order = field.field_order
            row.options = field.options
        else:
            template.fields.append(
                TemplateField(
                    field_label=field.field_label,
                    field_type=field.field_type,
                    is_required=field.is_required,
                    field_order=field.field_order,
                    options=field.options,
                )
            )

    _commit(db, template)
    return template


def soft_delete_template(db: Session, template: FormTemplate) -> None:
    from app.services import job_service  # local: job_service imports this module

    if job_service.job_references_template(db, template.template_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_TEMPLATE_IN_USE)
    template.deleted_at = datetime.now(UTC)
    db.commit()
