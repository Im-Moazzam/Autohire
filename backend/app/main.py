from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.recruiters import router as recruiters_router
from app.core.config import settings
from app.core.exceptions import ReauthRequired

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
    return JSONResponse(
        status_code=409,
        content={"code": "REAUTH_REQUIRED", "message": "Google authorization has expired."},
    )


api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(recruiters_router)
app.include_router(api_router)
