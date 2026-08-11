from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.google.session import google_call
from app.api.deps import get_current_recruiter
from app.core.crypto import decrypt_token, encrypt_token
from app.core.exceptions import ReauthRequired
from app.main import app
from app.models.api_usage_log import ApiName, ApiUsageLog
from app.models.recruiter import Recruiter, RecruiterState
from app.services.auth_service import SESSION_COOKIE, create_session_cookie

# A throwaway route with no try/except, proving the 409 conversion happens in
# the one app-level handler (main.py), not per-route.
_test_router = APIRouter()


@_test_router.get("/_test/google-call")
def _google_call_route(recruiter: Recruiter = Depends(get_current_recruiter)) -> dict[str, bool]:
    google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com/drive")
    return {"ok": True}


app.include_router(_test_router, prefix="/api/v1")


def _make_recruiter(
    db_session: Session,
    *,
    account_state: RecruiterState = RecruiterState.ACTIVE,
    expires_in: timedelta = timedelta(hours=1),
    access_token: str = "plain-access-token",
    refresh_token: str | None = "plain-refresh-token",
) -> Recruiter:
    recruiter = Recruiter(
        google_user_id=f"sub-{uuid4()}",
        email=f"{uuid4()}@example.com",
        full_name="Test Recruiter",
        google_access_token=encrypt_token(access_token),
        google_refresh_token=encrypt_token(refresh_token) if refresh_token else None,
        google_token_expires_at=datetime.now(UTC) + expires_in,
        granted_scopes=["openid"],
        account_state=account_state,
    )
    db_session.add(recruiter)
    db_session.commit()
    db_session.refresh(recruiter)
    return recruiter


def _response(status_code: int, json_body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code, json=json_body or {}, request=httpx.Request("GET", "https://example.com")
    )


def _refresh_response(
    access_token: str = "new-access-token", expires_in: int = 3600
) -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": access_token, "expires_in": expires_in},
        request=httpx.Request("POST", "https://oauth2.googleapis.com/token"),
    )


def _usage_rows(db_session: Session, recruiter_id) -> list[ApiUsageLog]:
    db_session.expire_all()
    return db_session.query(ApiUsageLog).filter_by(recruiter_id=recruiter_id).all()


def test_tc01_expired_access_token_refreshes_and_persists(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session, expires_in=timedelta(seconds=-10))

    with (
        patch("app.adapters.google.session.httpx.post", return_value=_refresh_response()),
        patch("app.adapters.google.session.httpx.request", return_value=_response(200)),
    ):
        response = google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert response.status_code == 200
    db_session.expire_all()
    stored = db_session.get(Recruiter, recruiter.recruiter_id)
    assert stored is not None
    assert decrypt_token(stored.google_access_token) == "new-access-token"
    assert stored.google_token_expires_at > datetime.now(UTC) + timedelta(minutes=30)


def test_tc02_invalid_grant_sets_reauth_required(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session, expires_in=timedelta(seconds=-10))

    with (
        patch(
            "app.adapters.google.session.httpx.post",
            return_value=_response(400, {"error": "invalid_grant"}),
        ),
        pytest.raises(ReauthRequired),
    ):
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    db_session.expire_all()
    stored = db_session.get(Recruiter, recruiter.recruiter_id)
    assert stored is not None
    assert stored.account_state == RecruiterState.REAUTH_REQUIRED


def test_tc03_reauth_required_route_returns_409(client: TestClient, db_session: Session) -> None:
    recruiter = _make_recruiter(db_session, account_state=RecruiterState.REAUTH_REQUIRED)
    client.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))

    response = client.get("/api/v1/_test/google-call")

    assert response.status_code == 409
    assert response.json() == {
        "code": "REAUTH_REQUIRED",
        "message": "Google authorization has expired.",
    }


def test_tc04_retries_429_twice_then_succeeds(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session)
    responses = [_response(429), _response(429), _response(200)]

    with (
        patch("app.adapters.google.session.httpx.request", side_effect=responses) as mock_request,
        patch("app.adapters.google.session.time.sleep"),
    ):
        response = google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert response.status_code == 200
    assert mock_request.call_count == 3
    rows = _usage_rows(db_session, recruiter.recruiter_id)
    assert len(rows) == 1
    assert rows[0].call_count == 3
    assert rows[0].api_name == ApiName.GOOGLE_DRIVE


def test_tc05_five_hundreds_fail_after_three_attempts(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session)
    responses = [_response(500), _response(500), _response(500), _response(500)]

    with (
        patch("app.adapters.google.session.httpx.request", side_effect=responses) as mock_request,
        patch("app.adapters.google.session.time.sleep"),
        pytest.raises(httpx.HTTPStatusError),
    ):
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert mock_request.call_count == 3
    rows = _usage_rows(db_session, recruiter.recruiter_id)
    assert len(rows) == 1
    assert rows[0].call_count == 3


def test_tc06_403_fails_immediately_no_retry(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session)

    with (
        patch(
            "app.adapters.google.session.httpx.request", return_value=_response(403)
        ) as mock_request,
        pytest.raises(httpx.HTTPStatusError),
    ):
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert mock_request.call_count == 1
    rows = _usage_rows(db_session, recruiter.recruiter_id)
    assert len(rows) == 1
    assert rows[0].call_count == 1


def test_tc09_successful_call_writes_exactly_one_log_row(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session)

    with patch("app.adapters.google.session.httpx.request", return_value=_response(200)):
        google_call(recruiter, ApiName.GOOGLE_CALENDAR, "GET", "https://example.com")

    rows = _usage_rows(db_session, recruiter.recruiter_id)
    assert len(rows) == 1
    assert rows[0].call_count == 1
    assert rows[0].api_name == ApiName.GOOGLE_CALENDAR


def test_401_then_429_429_shares_one_budget_of_three(db_session: Session) -> None:
    """401 forces a refresh but still counts against the shared 3-attempt
    budget — not a bonus retry on top of it."""
    recruiter = _make_recruiter(db_session)
    responses = [_response(401), _response(429), _response(429)]

    with (
        patch("app.adapters.google.session.httpx.request", side_effect=responses) as mock_request,
        patch(
            "app.adapters.google.session.httpx.post", return_value=_refresh_response()
        ) as mock_post,
        patch("app.adapters.google.session.time.sleep"),
        pytest.raises(httpx.HTTPStatusError),
    ):
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert mock_request.call_count == 3
    assert mock_post.call_count == 1
    rows = _usage_rows(db_session, recruiter.recruiter_id)
    assert len(rows) == 1
    assert rows[0].call_count == 3


def test_pre_call_reauth_required_writes_no_log_row(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session, account_state=RecruiterState.REAUTH_REQUIRED)

    with pytest.raises(ReauthRequired):
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert _usage_rows(db_session, recruiter.recruiter_id) == []


def test_caller_supplied_headers_are_merged_with_auth_header(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session)

    with patch(
        "app.adapters.google.session.httpx.request", return_value=_response(200)
    ) as mock_request:
        google_call(
            recruiter,
            ApiName.GOOGLE_DRIVE,
            "POST",
            "https://example.com",
            headers={"Content-Type": "application/json"},
        )

    sent_headers = mock_request.call_args.kwargs["headers"]
    assert sent_headers["Content-Type"] == "application/json"
    assert sent_headers["Authorization"] == "Bearer plain-access-token"


def test_second_call_with_same_recruiter_does_not_refresh_again(db_session: Session) -> None:
    """After a refresh, the in-memory recruiter object is updated so a second
    google_call() with the same instance doesn't re-trigger a refresh."""
    recruiter = _make_recruiter(db_session, expires_in=timedelta(seconds=-10))

    with (
        patch(
            "app.adapters.google.session.httpx.post", return_value=_refresh_response()
        ) as mock_post,
        patch("app.adapters.google.session.httpx.request", return_value=_response(200)),
    ):
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")
        google_call(recruiter, ApiName.GOOGLE_DRIVE, "GET", "https://example.com")

    assert mock_post.call_count == 1
