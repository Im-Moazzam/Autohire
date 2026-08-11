from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.google.oauth import GoogleTokens, GoogleUserInfo
from app.models.recruiter import Recruiter

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


def _login(client: TestClient) -> None:
    login_response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    redirect_url = login_response.headers["location"]
    state = redirect_url.split("state=")[1].split("&")[0]
    with (
        patch("app.api.routes.auth.exchange_code", return_value=FAKE_TOKENS),
        patch("app.api.routes.auth.fetch_userinfo", return_value=FAKE_USERINFO),
    ):
        client.get(
            "/api/v1/auth/google/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )


def test_tc03_patch_full_name(client: TestClient, db_session: Session) -> None:
    _login(client)

    response = client.patch("/api/v1/recruiters/me", json={"full_name": "New Name"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["email"] == "recruiter@example.com"

    recruiter = db_session.query(Recruiter).filter_by(google_user_id="google-sub-123").one()
    assert recruiter.full_name == "New Name"
    assert recruiter.email == "recruiter@example.com"


def test_tc04_patch_attempting_email_or_account_state_is_422(
    client: TestClient, db_session: Session
) -> None:
    _login(client)

    response = client.patch(
        "/api/v1/recruiters/me",
        json={"full_name": "New Name", "email": "attacker@example.com"},
    )

    assert response.status_code == 422
    recruiter = db_session.query(Recruiter).filter_by(google_user_id="google-sub-123").one()
    assert recruiter.email == "recruiter@example.com"
    assert recruiter.full_name == "Recruiter One"

    response = client.patch(
        "/api/v1/recruiters/me",
        json={"full_name": "New Name", "account_state": "SUSPENDED"},
    )

    assert response.status_code == 422
    recruiter = db_session.query(Recruiter).filter_by(google_user_id="google-sub-123").one()
    assert recruiter.account_state.value == "ACTIVE"


def test_tc05_patch_without_session_cookie_is_401(client: TestClient) -> None:
    response = client.patch("/api/v1/recruiters/me", json={"full_name": "New Name"})
    assert response.status_code == 401
