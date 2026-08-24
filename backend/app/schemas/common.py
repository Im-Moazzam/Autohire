from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

# pre-commit pins mypy==1.11.2, which doesn't support PEP 695 generic syntax yet
# (ruff's UP046/UP047 assume a newer mypy) — TypeVar/Generic until that's upgraded.
T = TypeVar("T")


class Page(BaseModel, Generic[T]):  # noqa: UP046
    items: list[T]
    total: int
    page: int
    size: int


class PaginationParams(BaseModel):
    page: int = 1
    size: int = 20


def pagination_params(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)


class ErrorOut(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """Build a `responses={}` dict declaring ErrorOut for each status, so every
    error shape a route can return reaches the generated TypeScript client (ADR-004 P7)."""
    return {status: {"model": ErrorOut} for status in statuses}
