import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.google.oauth import GoogleTokens, GoogleUserInfo
from app.core.config import settings
from app.main import app
from app.models.recruiter import Recruiter, RecruiterState
from app.services.auth_service import SESSION_COOKIE, create_session_cookie, upsert_recruiter

_ADMIN_EMAIL = "stub-recruiter@example.com"  # matches conftest's authed_client identity


@pytest.fixture(autouse=True)
def _admin_email_configured() -> Generator[None, None, None]:
    original = settings.admin_email
    settings.admin_email = _ADMIN_EMAIL
    yield
    settings.admin_email = original


def _other_client(recruiter: Recruiter) -> TestClient:
    other = TestClient(app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other


def test_non_admin_gets_403_from_every_admin_route(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    non_admin = _other_client(second_recruiter)
    assert non_admin.get("/api/v1/admin/recruiters").status_code == 403
    assert non_admin.get("/api/v1/admin/tasks").status_code == 403
    assert (
        non_admin.post(
            f"/api/v1/admin/recruiters/{authed_client.get('/api/v1/auth/me').json()['id']}/suspend"
        ).status_code
        == 403
    )


def test_admin_email_unset_disables_dashboard_for_everyone(authed_client: TestClient) -> None:
    settings.admin_email = ""
    response = authed_client.get("/api/v1/admin/recruiters")
    assert response.status_code == 403


def test_admin_can_list_recruiters(authed_client: TestClient, second_recruiter: Recruiter) -> None:
    response = authed_client.get("/api/v1/admin/recruiters")
    assert response.status_code == 200
    body = response.json()
    emails = {row["email"] for row in body["items"]}
    assert _ADMIN_EMAIL in emails
    assert second_recruiter.email in emails


def test_admin_usage_counts_not_cross_contaminated(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    """TC: per-recruiter row totals in the admin list must reflect only that
    recruiter's own data — the exact tenant-isolation failure mode this
    endpoint would have if the correlated subqueries were built wrong."""
    template = authed_client.post(
        "/api/v1/templates",
        json={
            "template_name": "Admin Test Template",
            "fields": [
                {
                    "field_label": "Email",
                    "field_type": "SHORT_TEXT",
                    "is_required": True,
                    "field_order": 0,
                },
                {
                    "field_label": "Full Name",
                    "field_type": "SHORT_TEXT",
                    "is_required": True,
                    "field_order": 1,
                },
            ],
        },
    ).json()
    authed_client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Admin-owned job",
            "job_description": "d",
            "template_id": template["template_id"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )

    response = authed_client.get("/api/v1/admin/recruiters")
    rows = {row["email"]: row for row in response.json()["items"]}
    assert rows[_ADMIN_EMAIL]["total_jobs"] == 1
    assert rows[second_recruiter.email]["total_jobs"] == 0


def test_admin_cannot_suspend_self(authed_client: TestClient) -> None:
    admin_id = authed_client.get("/api/v1/auth/me").json()["id"]
    response = authed_client.post(f"/api/v1/admin/recruiters/{admin_id}/suspend")
    assert response.status_code == 400
    assert response.json()["code"] == "CANNOT_SUSPEND_SELF"


def test_suspend_then_reactivate_round_trip(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    response = authed_client.post(
        f"/api/v1/admin/recruiters/{second_recruiter.recruiter_id}/suspend"
    )
    assert response.status_code == 200
    assert response.json()["account_state"] == "SUSPENDED"
    db_session.refresh(second_recruiter)
    assert second_recruiter.account_state == RecruiterState.SUSPENDED

    response = authed_client.post(
        f"/api/v1/admin/recruiters/{second_recruiter.recruiter_id}/reactivate"
    )
    assert response.status_code == 200
    assert response.json()["account_state"] == "ACTIVE"


def test_suspended_recruiter_session_is_rejected(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    authed_client.post(f"/api/v1/admin/recruiters/{second_recruiter.recruiter_id}/suspend")

    suspended = _other_client(second_recruiter)
    response = suspended.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_login_does_not_resurrect_a_suspended_recruiter(
    second_recruiter: Recruiter, db_session: Session
) -> None:
    """Regression test for the exact bug the `ponytail:` comment in
    auth_service.py flagged: upsert_recruiter used to unconditionally
    overwrite account_state on every login, silently un-suspending anyone
    who simply logged in again."""
    second_recruiter.account_state = RecruiterState.SUSPENDED
    db_session.commit()

    tokens = GoogleTokens(
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        expires_in=3600,
        granted_scopes=[
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "openid",
            "email",
            "profile",
        ],
    )
    userinfo = GoogleUserInfo(
        sub="stub-recruiter-2-sub",
        email=second_recruiter.email,
        name=second_recruiter.full_name,
        picture=None,
    )

    result = upsert_recruiter(db_session, tokens, userinfo)
    assert result.account_state == RecruiterState.SUSPENDED
    assert uuid.UUID(str(result.recruiter_id)) == second_recruiter.recruiter_id
