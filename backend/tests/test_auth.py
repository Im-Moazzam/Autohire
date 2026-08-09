from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.google.oauth import GoogleTokens, GoogleUserInfo
from app.models.recruiter import Recruiter, RecruiterState

FULL_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "openid",
    "email",
    "profile",
]

FAKE_TOKENS = GoogleTokens(
    access_token="fake-access-token",
    refresh_token="fake-refresh-token",
    expires_in=3600,
    granted_scopes=FULL_SCOPES,
)
FAKE_USERINFO = GoogleUserInfo(
    sub="google-sub-123",
    email="recruiter@example.com",
    name="Recruiter One",
    picture="https://example.com/pic.jpg",
)


def _start_login(client: TestClient) -> tuple[str, str]:
    """Hit /login to obtain a valid (state cookie, state param) pair."""
    login_response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    redirect_url = login_response.headers["location"]
    state_param = redirect_url.split("state=")[1].split("&")[0]
    return client.cookies["autohire_oauth_state"], state_param


def test_login_redirects_with_required_scopes_and_state(client: TestClient) -> None:
    response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert "access_type=offline" in location
    assert "prompt=consent" in location
    assert "state=" in location
    for scope in ["drive.file", "gmail.send", "calendar", "openid", "email", "profile"]:
        assert scope in location
    assert "autohire_oauth_state" in response.cookies


def test_tc01_first_time_consent_granted(client: TestClient, db_session: Session) -> None:
    _, state = _start_login(client)

    with (
        patch("app.api.routes.auth.exchange_code", return_value=FAKE_TOKENS),
        patch("app.api.routes.auth.fetch_userinfo", return_value=FAKE_USERINFO),
    ):
        response = client.get(
            "/api/v1/auth/google/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"].endswith("/dashboard")
    assert "autohire_session" in response.cookies

    recruiter = db_session.query(Recruiter).filter_by(google_user_id="google-sub-123").one()
    assert recruiter.account_state == RecruiterState.ACTIVE
    assert recruiter.google_access_token != "fake-access-token"
    assert recruiter.google_refresh_token != "fake-refresh-token"


def test_tc02_returning_recruiter_no_duplicate(client: TestClient, db_session: Session) -> None:
    for _ in range(2):
        _, state = _start_login(client)
        with (
            patch("app.api.routes.auth.exchange_code", return_value=FAKE_TOKENS),
            patch("app.api.routes.auth.fetch_userinfo", return_value=FAKE_USERINFO),
        ):
            client.get(
                "/api/v1/auth/google/callback",
                params={"code": "auth-code", "state": state},
                follow_redirects=False,
            )

    rows = db_session.query(Recruiter).filter_by(google_user_id="google-sub-123").all()
    assert len(rows) == 1


def test_tc03_consent_denied_no_row_no_crash(client: TestClient, db_session: Session) -> None:
    response = client.get(
        "/api/v1/auth/google/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert response.status_code == 307
    assert response.headers["location"].endswith("/auth/error")
    assert db_session.query(Recruiter).count() == 0


def test_tc04_tampered_state_rejected(client: TestClient) -> None:
    _start_login(client)  # sets a valid state cookie
    with patch("app.api.routes.auth.exchange_code") as mock_exchange:
        response = client.get(
            "/api/v1/auth/google/callback",
            params={"code": "auth-code", "state": "tampered-garbage"},
            follow_redirects=False,
        )
    assert response.status_code == 400
    mock_exchange.assert_not_called()


def test_tc05_me_without_cookie_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_missing_required_scope_sets_reauth_required(
    client: TestClient, db_session: Session
) -> None:
    _, state = _start_login(client)
    partial_tokens = GoogleTokens(
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        expires_in=3600,
        granted_scopes=["openid", "email", "profile"],  # drive/gmail/calendar denied
    )
    with (
        patch("app.api.routes.auth.exchange_code", return_value=partial_tokens),
        patch("app.api.routes.auth.fetch_userinfo", return_value=FAKE_USERINFO),
    ):
        client.get(
            "/api/v1/auth/google/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )

    recruiter = db_session.query(Recruiter).filter_by(google_user_id="google-sub-123").one()
    assert recruiter.account_state == RecruiterState.REAUTH_REQUIRED


def test_me_returns_recruiter_and_never_leaks_tokens(
    client: TestClient, db_session: Session
) -> None:
    _, state = _start_login(client)
    with (
        patch("app.api.routes.auth.exchange_code", return_value=FAKE_TOKENS),
        patch("app.api.routes.auth.fetch_userinfo", return_value=FAKE_USERINFO),
    ):
        callback_response = client.get(
            "/api/v1/auth/google/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )

    for body in (callback_response.text,):
        assert "fake-access-token" not in body
        assert "fake-refresh-token" not in body

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["email"] == "recruiter@example.com"
    assert body["account_state"] == "ACTIVE"
    assert "google_access_token" not in body
    assert "google_refresh_token" not in body
    assert "fake-access-token" not in me_response.text
    assert "fake-refresh-token" not in me_response.text
