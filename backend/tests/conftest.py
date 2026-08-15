from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.google.oauth import GoogleTokens, GoogleUserInfo
from app.api.deps import get_db
from app.core.db import SessionLocal
from app.main import app
from app.models.api_usage_log import ApiUsageLog
from app.models.recruiter import Recruiter, RecruiterState
from app.models.template import FormTemplate


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    yield session
    session.query(ApiUsageLog).delete()
    session.query(FormTemplate).delete()
    session.query(Recruiter).delete()
    session.commit()
    session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


_STUB_TEST_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "openid",
    "email",
    "profile",
]
_STUB_TEST_TOKENS = GoogleTokens(
    access_token="fake-access-token",
    refresh_token="fake-refresh-token",
    expires_in=3600,
    granted_scopes=_STUB_TEST_SCOPES,
)
_STUB_TEST_USERINFO = GoogleUserInfo(
    sub="stub-recruiter-sub",
    email="stub-recruiter@example.com",
    name="Stub Recruiter",
    picture=None,
)


@pytest.fixture
def authed_client(client: TestClient) -> TestClient:
    """A logged-in client for TS-02 stub-route tests, which only need a real
    session cookie — not any particular recruiter identity."""
    login_response = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state = login_response.headers["location"].split("state=")[1].split("&")[0]
    with (
        patch("app.api.routes.auth.exchange_code", return_value=_STUB_TEST_TOKENS),
        patch("app.api.routes.auth.fetch_userinfo", return_value=_STUB_TEST_USERINFO),
    ):
        client.get(
            "/api/v1/auth/google/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )
    return client


@pytest.fixture
def second_recruiter(db_session: Session) -> Recruiter:
    """A second recruiter row, inserted directly (no login flow needed), so
    cross-tenant tests (TC-08) can prove one recruiter's template is 404 for
    another without depending on `authed_client`'s identity."""
    recruiter = Recruiter(
        google_user_id="stub-recruiter-2-sub",
        email="stub-recruiter-2@example.com",
        full_name="Stub Recruiter Two",
        google_access_token="fake-access-token-2",
        google_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        granted_scopes=[],
        account_state=RecruiterState.ACTIVE,
    )
    db_session.add(recruiter)
    db_session.commit()
    db_session.refresh(recruiter)
    return recruiter
