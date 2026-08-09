from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.adapters.google.oauth import build_auth_url, exchange_code, fetch_userinfo
from app.api.deps import get_current_recruiter, get_db
from app.core.config import settings
from app.models.recruiter import Recruiter
from app.schemas.recruiter import RecruiterOut
from app.services.auth_service import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    STATE_COOKIE,
    STATE_MAX_AGE,
    create_session_cookie,
    generate_state,
    upsert_recruiter,
    verify_state,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_SECURE = settings.app_env != "local"


@router.get("/google/login")
def google_login() -> RedirectResponse:
    nonce, signed_state = generate_state()
    response = RedirectResponse(url=build_auth_url(signed_state), status_code=307)
    response.set_cookie(
        STATE_COOKIE,
        nonce,
        max_age=STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
    )
    return response


@router.get("/google/callback")
def google_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    oauth_state: str | None = Cookie(default=None, alias=STATE_COOKIE),
) -> RedirectResponse:
    if error:
        response = RedirectResponse(url=f"{settings.frontend_url}/auth/error", status_code=307)
        response.delete_cookie(STATE_COOKIE)
        return response

    if not verify_state(oauth_state, state) or not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid state")

    tokens = exchange_code(code)
    userinfo = fetch_userinfo(tokens.access_token)
    recruiter = upsert_recruiter(db, tokens, userinfo)

    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard", status_code=307)
    response.delete_cookie(STATE_COOKIE)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_cookie(str(recruiter.recruiter_id)),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
    )
    return response


@router.get("/me", response_model=RecruiterOut)
def get_me(recruiter: Recruiter = Depends(get_current_recruiter)) -> Recruiter:
    return recruiter
