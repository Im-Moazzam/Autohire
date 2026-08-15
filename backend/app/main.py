from fastapi import APIRouter, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.auth import router as auth_router
from app.api.routes.candidates import candidates_router, job_candidates_router
from app.api.routes.emails import router as emails_router
from app.api.routes.interviews import router as interviews_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.public import router as public_router
from app.api.routes.recruiters import router as recruiters_router
from app.api.routes.scheduling import router as scheduling_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.templates import router as templates_router
from app.core.config import settings
from app.core.exceptions import ReauthRequired
from app.schemas.common import ErrorOut

app = FastAPI(title="AutoHire")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ReauthRequired)
def reauth_required_handler(request: Request, exc: ReauthRequired) -> JSONResponse:
    body = ErrorOut(code="REAUTH_REQUIRED", message="Google authorization has expired.")
    return JSONResponse(status_code=409, content=body.model_dump())


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """ADR-004 P7/P9: every error is ErrorOut. Registered on Starlette's
    HTTPException (fastapi.HTTPException subclasses it) so this also catches
    routing-level 404/405s that FastAPI raises directly, not just app code.
    A route that wants a specific code raises with detail={"code", "message",
    "details"}; anything else (a bare string detail, or Starlette's own
    routing exceptions) gets a generic code derived from the status."""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        body = ErrorOut(
            code=exc.detail["code"],
            message=exc.detail.get("message", ""),
            details=exc.detail.get("details"),
        )
    else:
        body = ErrorOut(code=f"HTTP_{exc.status_code}", message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """extra="forbid" violations and body/query validation failures raise this
    before any route body runs, so they bypass the HTTPException handler above
    entirely. Field-level errors are preserved under `details`, not flattened,
    so the frontend can mark individual inputs invalid."""
    body = ErrorOut(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": jsonable_encoder(exc.errors())},
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(recruiters_router)
api_router.include_router(templates_router)
api_router.include_router(jobs_router)
api_router.include_router(public_router)
api_router.include_router(job_candidates_router)
api_router.include_router(candidates_router)
api_router.include_router(tasks_router)
api_router.include_router(scheduling_router)
api_router.include_router(interviews_router)
api_router.include_router(emails_router)
app.include_router(api_router)
