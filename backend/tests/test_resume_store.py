from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from app.adapters.resume_store import DriveResumeStore
from app.core.crypto import encrypt_token
from app.models.api_usage_log import ApiName, ApiUsageLog
from app.models.recruiter import Recruiter, RecruiterState


def _make_recruiter(db_session: Session) -> Recruiter:
    recruiter = Recruiter(
        google_user_id=f"sub-{uuid4()}",
        email=f"{uuid4()}@example.com",
        full_name="Cloud Recruiter",
        google_access_token=encrypt_token("plain-access-token"),
        google_refresh_token=encrypt_token("plain-refresh-token"),
        google_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
        granted_scopes=["openid"],
        account_state=RecruiterState.ACTIVE,
    )
    db_session.add(recruiter)
    db_session.commit()
    db_session.refresh(recruiter)
    return recruiter


def test_drive_resume_store_goes_through_google_call_and_logs_once(db_session: Session) -> None:
    recruiter = _make_recruiter(db_session)
    response = httpx.Response(
        200,
        json={"id": "drive-folder-123"},
        request=httpx.Request("POST", "https://example.com"),
    )

    with patch("app.adapters.google.session.httpx.request", return_value=response) as mock_request:
        folder_id = DriveResumeStore().create_job_folder(recruiter, uuid4(), "Backend Engineer")

    assert folder_id == "drive-folder-123"
    assert mock_request.call_count == 1

    db_session.expire_all()
    rows = db_session.query(ApiUsageLog).filter_by(recruiter_id=recruiter.recruiter_id).all()
    assert len(rows) == 1
    assert rows[0].call_count == 1
    assert rows[0].api_name == ApiName.GOOGLE_DRIVE
