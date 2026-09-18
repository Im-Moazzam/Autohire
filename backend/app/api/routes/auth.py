from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.adapters.google.oauth import build_auth_url, exchange_code, fetch_userinfo
from app.api.deps import get_current_recruiter, get_db
from app.core.config import settings
from app.models.recruiter import Recruiter
from app.schemas.common import error_responses
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


def _redirect_to_google_consent(request: Request) -> RedirectResponse:
    # Built from the incoming request's own host, not a fixed setting, so this
    # works whether the client reached the API via localhost (web app) or a
    # LAN IP (phone) — Google requires this to exactly match the redirect_uri
    # used in the later token exchange, which google_callback below derives
    # the same way (the callback request arrives at whichever host Google was
    # given here, so both computations agree).
    redirect_uri = str(request.url_for("google_callback"))
    nonce, signed_state = generate_state()
    response = RedirectResponse(url=build_auth_url(signed_state, redirect_uri), status_code=307)
    response.set_cookie(
        STATE_COOKIE,
        nonce,
        max_age=STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
    )
    return response


@router.get("/google/login")
def google_login(request: Request) -> RedirectResponse:
    return _redirect_to_google_consent(request)


@router.get("/google/reconnect")
def google_reconnect(
    request: Request, recruiter: Recruiter = Depends(get_current_recruiter)
) -> RedirectResponse:
    """Restart consent for the logged-in recruiter. Reuses the same state-binding
    CSRF cookie as /google/login; the existing /google/callback + upsert_recruiter
    already replace the stored tokens and flip account_state back to ACTIVE
    (retaining the existing refresh token if Google omits a new one)."""
    return _redirect_to_google_consent(request)


@router.get("/google/callback")
def google_callback(
    request: Request,
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

    redirect_uri = str(request.url_for("google_callback"))
    tokens = exchange_code(code, redirect_uri)
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


@router.get("/me", response_model=RecruiterOut, responses=error_responses(401))
def get_me(recruiter: Recruiter = Depends(get_current_recruiter)) -> Recruiter:
    return recruiter


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    """No get_current_recruiter dependency, deliberately — logout must be
    idempotent with no session (AC-02), not 401. Safe without CSRF protection
    because the session cookie is SameSite=Lax: a cross-site POST doesn't carry
    it, so an attacker can't trigger this against a logged-in victim."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", secure=_COOKIE_SECURE)
    return response
