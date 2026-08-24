import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.calendar_store import GoogleCalendarStore
from app.adapters.mailer import GmailMailer
from app.core.crypto import encrypt_token
from app.main import app
from app.models.api_usage_log import ApiName, ApiUsageLog
from app.models.candidate import Candidate
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.recruiter import Recruiter, RecruiterState
from app.models.scheduling import SchedulingPreference
from app.schemas.enums import DeliveryStatus, SlotStatus
from app.services.auth_service import SESSION_COOKIE, create_session_cookie
from app.tasks.email_dispatch import email_dispatch_job


# TS-06/R-04: POST /emails/send (manual, ad hoc send) is genuinely Phase 2 —
# it must say so honestly instead of returning a stale fixture TaskOut whose
# task_id 404s at GET /tasks/{id}.
def test_send_email_is_501_not_implemented(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/emails/send",
        json={"email_type": "CUSTOM", "candidate_ids": [str(uuid.uuid4())]},
    )
    assert response.status_code == 501
    assert response.json()["code"] == "NOT_IMPLEMENTED"


def _other_client(recruiter: Recruiter) -> TestClient:
    other = TestClient(app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other


def _create_job(client: TestClient) -> dict:
    template = client.post(
        "/api/v1/templates",
        json={
            "template_name": f"Email Story Role {uuid.uuid4()}",
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
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Backend Engineer",
            "job_description": "Backend role needing python and sql.",
            "template_id": template["template_id"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _make_slot(db_session: Session, recruiter: Recruiter, job: dict) -> InterviewSlot:
    db_session.add(
        SchedulingPreference(
            recruiter_id=recruiter.recruiter_id,
            available_days=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
            available_start_time=datetime(2026, 1, 1, 9, 0).time(),
            available_end_time=datetime(2026, 1, 1, 17, 0).time(),
            slot_duration_minutes=30,
            timezone="UTC",
        )
    )
    candidate = Candidate(
        job_id=job["job_id"],
        full_name="Jane Candidate",
        email="jane@example.com",
        submission_status="INVITED",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(candidate)
    db_session.flush()

    slot = InterviewSlot(
        candidate_id=candidate.candidate_id,
        job_id=job["job_id"],
        recruiter_id=recruiter.recruiter_id,
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
        duration_minutes=30,
        status=SlotStatus.PENDING,
        google_calendar_event_id="cal-abc",
        google_meet_link="https://meet.local.test/abc",
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)
    return slot


def _get_recruiter(db_session: Session) -> Recruiter:
    return db_session.query(Recruiter).filter_by(google_user_id="stub-recruiter-sub").one()


# TC-07
def test_retry_is_a_no_op(authed_client: TestClient, db_session: Session) -> None:
    recruiter = _get_recruiter(db_session)
    job = _create_job(authed_client)
    slot = _make_slot(db_session, recruiter, job)

    with patch("app.tasks.email_dispatch.get_mailer") as mock_get_mailer:
        fake_mailer = Mock(send=Mock(return_value=Mock(message_id="msg-1", thread_id="thread-1")))
        mock_get_mailer.return_value = fake_mailer

        email_dispatch_job.run(str(slot.slot_id))
        email_dispatch_job.run(str(slot.slot_id))

    assert fake_mailer.send.call_count == 1
    logs = db_session.query(EmailLog).all()
    assert len(logs) == 1
    assert logs[0].delivery_status == DeliveryStatus.SENT


# TC-08
def test_mailer_failure_leaves_slot_and_records_failure(
    authed_client: TestClient, db_session: Session
) -> None:
    recruiter = _get_recruiter(db_session)
    job = _create_job(authed_client)
    slot = _make_slot(db_session, recruiter, job)

    with patch("app.tasks.email_dispatch.get_mailer") as mock_get_mailer:
        mock_get_mailer.return_value = Mock(send=Mock(side_effect=RuntimeError("smtp down")))
        email_dispatch_job.run(str(slot.slot_id))

    db_session.refresh(slot)
    assert slot.status == SlotStatus.PENDING  # the interview survives

    log = db_session.query(EmailLog).one()
    assert log.delivery_status == DeliveryStatus.FAILED

    # Retryable: a fixed Mailer can be retried by re-running the same slot —
    # but per the idempotency design, the existing row means the attempt is
    # visible (FAILED), not silently lost.
    assert log.candidate_id == slot.candidate_id


def test_list_emails_is_paginated_and_recruiter_scoped(
    authed_client: TestClient, db_session: Session, second_recruiter: Recruiter
) -> None:
    recruiter = _get_recruiter(db_session)
    job = _create_job(authed_client)
    slot = _make_slot(db_session, recruiter, job)

    with patch("app.tasks.email_dispatch.get_mailer") as mock_get_mailer:
        mock_get_mailer.return_value = Mock(
            send=Mock(return_value=Mock(message_id="msg-1", thread_id="thread-1"))
        )
        email_dispatch_job.run(str(slot.slot_id))

    own = authed_client.get("/api/v1/emails")
    assert own.status_code == 200
    body = own.json()
    assert set(body.keys()) == {"items", "total", "page", "size"}
    assert body["total"] == 1
    assert body["items"][0]["candidate_name"]

    other = _other_client(second_recruiter)
    cross = other.get("/api/v1/emails")
    assert cross.status_code == 200
    assert cross.json()["total"] == 0


def test_list_emails_filters_by_job(authed_client: TestClient, db_session: Session) -> None:
    recruiter = _get_recruiter(db_session)
    job = _create_job(authed_client)
    slot = _make_slot(db_session, recruiter, job)

    with patch("app.tasks.email_dispatch.get_mailer") as mock_get_mailer:
        mock_get_mailer.return_value = Mock(
            send=Mock(return_value=Mock(message_id="msg-1", thread_id="thread-1"))
        )
        email_dispatch_job.run(str(slot.slot_id))

    response = authed_client.get("/api/v1/emails", params={"job_id": job["job_id"]})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = authed_client.get("/api/v1/emails", params={"job_id": str(uuid.uuid4())})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def _make_recruiter_with_google(db_session: Session) -> Recruiter:
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


def test_gmail_mailer_goes_through_google_call_and_logs_once(db_session: Session) -> None:
    recruiter = _make_recruiter_with_google(db_session)
    response = httpx.Response(
        200,
        json={"id": "gmail-msg-1", "threadId": "gmail-thread-1"},
        request=httpx.Request("POST", "https://example.com"),
    )

    with patch("app.adapters.google.session.httpx.request", return_value=response) as mock_request:
        sent = GmailMailer().send(recruiter, to="a@example.com", subject="Hi", body="Body")

    assert sent.message_id == "gmail-msg-1"
    assert mock_request.call_count == 1

    db_session.expire_all()
    rows = db_session.query(ApiUsageLog).filter_by(recruiter_id=recruiter.recruiter_id).all()
    assert len(rows) == 1
    assert rows[0].api_name == ApiName.GOOGLE_GMAIL


def test_google_calendar_store_goes_through_google_call_and_logs_once(db_session: Session) -> None:
    recruiter = _make_recruiter_with_google(db_session)
    response = httpx.Response(
        200,
        json={
            "id": "cal-event-1",
            "conferenceData": {
                "entryPoints": [{"entryPointType": "video", "uri": "https://meet.google.com/xyz"}]
            },
        },
        request=httpx.Request("POST", "https://example.com"),
    )

    with patch("app.adapters.google.session.httpx.request", return_value=response) as mock_request:
        event = GoogleCalendarStore().create_event(
            recruiter,
            summary="Interview",
            description="desc",
            starts_at=datetime.now(UTC),
            duration_minutes=30,
            attendee_email="candidate@example.com",
        )

    assert event.event_id == "cal-event-1"
    assert event.meet_link == "https://meet.google.com/xyz"
    assert mock_request.call_count == 1

    db_session.expire_all()
    rows = db_session.query(ApiUsageLog).filter_by(recruiter_id=recruiter.recruiter_id).all()
    assert len(rows) == 1
    assert rows[0].api_name == ApiName.GOOGLE_CALENDAR
