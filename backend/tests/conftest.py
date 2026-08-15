from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.google.oauth import GoogleTokens, GoogleUserInfo
from app.api import fixtures
from app.api.deps import get_db
from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models.api_usage_log import ApiUsageLog
from app.models.job import JobPosting
from app.models.recruiter import Recruiter, RecruiterState
from app.models.template import FormTemplate


@pytest.fixture(autouse=True)
def _local_storage_root(tmp_path: Path) -> Generator[None, None, None]:
    """LocalResumeStore writes here (APP_ENV=local) — point it at a per-test
    tmp_path so tests never touch the real /storage mount or a bare host root."""
    original = settings.local_storage_root
    settings.local_storage_root = str(tmp_path)
    yield
    settings.local_storage_root = original


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    yield session
    # FK order: JobPosting references FormTemplate, so it must go first.
    session.query(JobPosting).delete()
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
def seeded_stub_jobs(authed_client: TestClient, db_session: Session) -> list[JobPosting]:
    """Mirrors fixtures.JOBS (and the two fixture templates they reference) as
    real rows under the authed recruiter, so stub routes that now query real
    tables via get_owned_job (candidates, process) still have a job to find."""
    recruiter = db_session.query(Recruiter).filter_by(google_user_id="stub-recruiter-sub").one()

    for template_id, template in fixtures.TEMPLATES.items():
        db_session.add(
            FormTemplate(
                template_id=template_id,
                recruiter_id=recruiter.recruiter_id,
                template_name=template["template_name"],
                created_at=template["created_at"],
                updated_at=template["updated_at"],
            )
        )
    db_session.flush()

    jobs = []
    for job_id, job in fixtures.JOBS.items():
        row = JobPosting(
            job_id=job_id,
            recruiter_id=recruiter.recruiter_id,
            template_id=job["template_id"],
            job_title=job["job_title"],
            job_description=job["job_description"],
            google_drive_folder_id=job["google_drive_folder_id"],
            apply_slug=job["apply_slug"],
            status=job["status"],
            is_accepting_responses=job["is_accepting_responses"],
            expires_at=job["expires_at"],
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )
        db_session.add(row)
        jobs.append(row)
    db_session.commit()
    return jobs


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
