from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_recruiter, get_db, get_owned_template
from app.models.recruiter import Recruiter
from app.models.template import FormTemplate
from app.schemas.common import (
    Page,
    PaginationParams,
    error_responses,
    pagination_params,
)
from app.schemas.template import TemplateCreate, TemplateOut, TemplateReplace
from app.services import template_service

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("", response_model=Page[TemplateOut], responses=error_responses(401))
def list_templates(
    params: PaginationParams = Depends(pagination_params),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> Page[TemplateOut]:
    items, total = template_service.list_templates(db, recruiter.recruiter_id, params)
    return Page[TemplateOut](
        items=[TemplateOut.model_validate(item) for item in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "",
    response_model=TemplateOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(401, 409, 422),
)
def create_template(
    payload: TemplateCreate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: Session = Depends(get_db),
) -> FormTemplate:
    return template_service.create_template(
        db, recruiter.recruiter_id, payload.template_name, payload.fields
    )


@router.get("/{template_id}", response_model=TemplateOut, responses=error_responses(401, 404))
def get_template(template: FormTemplate = Depends(get_owned_template)) -> FormTemplate:
    return template


@router.put(
    "/{template_id}",
    response_model=TemplateOut,
    responses=error_responses(401, 404, 409, 422),
)
def replace_template(
    payload: TemplateReplace,
    template: FormTemplate = Depends(get_owned_template),
    db: Session = Depends(get_db),
) -> FormTemplate:
    """Replaces the full field set: the client sends the whole ordered array,
    the server reconciles it against existing rows by `field_id` (keep/update
    when present, insert when absent, delete when missing from the payload) —
    this is not a partial update."""
    return template_service.replace_template(db, template, payload.template_name, payload.fields)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 404, 409),
)
def delete_template(
    template: FormTemplate = Depends(get_owned_template),
    db: Session = Depends(get_db),
) -> Response:
    template_service.soft_delete_template(db, template)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
