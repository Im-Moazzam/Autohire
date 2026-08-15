import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api import fixtures
from app.api.deps import get_current_recruiter, get_owned_template
from app.schemas.common import (
    Page,
    PaginationParams,
    error_responses,
    paginate,
    pagination_params,
)
from app.schemas.template import TemplateCreate, TemplateOut, TemplateReplace

router = APIRouter(
    prefix="/templates",
    tags=["templates"],
    dependencies=[Depends(get_current_recruiter)],
)


@router.get("", response_model=Page[TemplateOut], responses=error_responses(401))
def list_templates(params: PaginationParams = Depends(pagination_params)) -> Page[TemplateOut]:
    # STUB: US-04
    items = [TemplateOut(**t) for t in fixtures.TEMPLATES.values()]
    return paginate(items, params)


@router.post(
    "",
    response_model=TemplateOut,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(401, 422),
)
def create_template(payload: TemplateCreate) -> TemplateOut:
    # STUB: US-04 — echoes the payload back as a new fixture-shaped template.
    first = next(iter(fixtures.TEMPLATES.values()))
    return TemplateOut(
        template_id=uuid.uuid4(),
        template_name=payload.template_name,
        fields=[
            {**field.model_dump(), "field_id": field.field_id or uuid.uuid4()}
            for field in payload.fields
        ],
        created_at=first["created_at"],
        updated_at=first["created_at"],
    )


@router.get("/{template_id}", response_model=TemplateOut, responses=error_responses(401, 404))
def get_template(template: dict = Depends(get_owned_template)) -> TemplateOut:
    # STUB: US-04
    return TemplateOut(**template)


@router.put("/{template_id}", response_model=TemplateOut, responses=error_responses(401, 404, 422))
def replace_template(
    payload: TemplateReplace, template: dict = Depends(get_owned_template)
) -> TemplateOut:
    # STUB: US-04 — TemplateFieldIn.field_id present means "keep this row"; a
    # real implementation reconciles by field_id rather than delete-and-recreate,
    # since candidate_form_responses.field_id is an FK.
    return TemplateOut(
        template_id=template["template_id"],
        template_name=payload.template_name,
        fields=[
            {**field.model_dump(), "field_id": field.field_id or uuid.uuid4()}
            for field in payload.fields
        ],
        created_at=template["created_at"],
        updated_at=template["created_at"],
    )


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 404, 409),
)
def delete_template(template: dict = Depends(get_owned_template)) -> Response:
    # STUB: US-04 — soft delete; 409 TEMPLATE_IN_USE if referenced by a LIVE job.
    in_use = any(
        job["template_id"] == template["template_id"] and job["status"] == "LIVE"
        for job in fixtures.JOBS.values()
    )
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "TEMPLATE_IN_USE", "message": "Template is used by a LIVE job."},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
