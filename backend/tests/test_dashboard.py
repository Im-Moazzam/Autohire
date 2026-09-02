import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.candidate import Candidate
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.recruiter import Recruiter
from app.services.auth_service import SESSION_COOKIE, create_session_cookie


def _create_template(client: TestClient, name: str = "Standard Software Role") -> dict:
    response = client.post(
        "/api/v1/templates",
        json={
            "template_name": name,
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
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_job(client: TestClient, template_id: str, title: str = "New Role") -> dict:
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": title,
            "job_description": "Own the API layer.",
            "template_id": template_id,
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _other_client(recruiter: Recruiter) -> TestClient:
    other = TestClient(app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other


def test_stats_zero_for_recruiter_with_nothing(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_jobs"] == 0
    assert body["total_candidates"] == 0
    assert body["total_interviews"] == 0
    assert body["total_emails"] == 0
    # Zero-filled across every enum member, not just the ones with data.
    assert body["jobs_by_status"] == {
        "DRAFT": 0,
        "LIVE": 0,
        "CLOSED": 0,
        "PROCESSED": 0,
    }


def test_stats_counts_jobs_by_status(authed_client: TestClient) -> None:
    template = _create_template(authed_client)
    _create_job(authed_client, template["template_id"], "Live Job")
    job2 = _create_job(authed_client, template["template_id"], "Closed Job")
    authed_client.patch(f"/api/v1/jobs/{job2['job_id']}", json={"status": "CLOSED"})

    response = authed_client.get("/api/v1/dashboard/stats")
    body = response.json()
    assert body["total_jobs"] == 2
    assert body["jobs_by_status"]["LIVE"] == 1
    assert body["jobs_by_status"]["CLOSED"] == 1


def test_stats_counts_candidates_across_jobs(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job1 = _create_job(authed_client, template["template_id"], "Job One")
    job2 = _create_job(authed_client, template["template_id"], "Job Two")

    db_session.add_all(
        [
            Candidate(
                job_id=uuid.UUID(job1["job_id"]),
                full_name="A",
                email="a@example.com",
                submission_status="SUBMITTED",
                submitted_at=datetime.now(UTC),
            ),
            Candidate(
                job_id=uuid.UUID(job2["job_id"]),
                full_name="B",
                email="b@example.com",
                submission_status="RANKED",
                submitted_at=datetime.now(UTC),
            ),
        ]
    )
    db_session.commit()

    response = authed_client.get("/api/v1/dashboard/stats")
    body = response.json()
    assert body["total_candidates"] == 2
    assert body["candidates_by_status"]["SUBMITTED"] == 1
    assert body["candidates_by_status"]["RANKED"] == 1


def test_stats_excludes_soft_deleted_candidates(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    db_session.add(
        Candidate(
            job_id=uuid.UUID(job["job_id"]),
            full_name="Gone",
            email="gone@example.com",
            submission_status="SUBMITTED",
            submitted_at=datetime.now(UTC),
            deleted_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    response = authed_client.get("/api/v1/dashboard/stats")
    assert response.json()["total_candidates"] == 0


def test_stats_counts_interviews_and_emails(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = Candidate(
        job_id=uuid.UUID(job["job_id"]),
        full_name="C",
        email="c@example.com",
        submission_status="RANKED",
        submitted_at=datetime.now(UTC),
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    recruiter_id = uuid.UUID(authed_client.get("/api/v1/auth/me").json()["id"])

    db_session.add(
        InterviewSlot(
            candidate_id=candidate.candidate_id,
            job_id=uuid.UUID(job["job_id"]),
            recruiter_id=recruiter_id,
            scheduled_at=datetime.now(UTC),
            duration_minutes=30,
            status="PENDING",
        )
    )
    db_session.add(
        EmailLog(
            recruiter_id=recruiter_id,
            candidate_id=candidate.candidate_id,
            email_type="INTERVIEW_INVITE",
            subject="Interview invitation",
            idempotency_key=f"{candidate.candidate_id}:INTERVIEW_INVITE:none",
            delivery_status="SENT",
        )
    )
    db_session.commit()

    response = authed_client.get("/api/v1/dashboard/stats")
    body = response.json()
    assert body["total_interviews"] == 1
    assert body["interviews_by_status"]["PENDING"] == 1
    assert body["total_emails"] == 1
    assert body["emails_by_status"]["SENT"] == 1


def test_stats_scoped_to_calling_recruiter_only(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    template = _create_template(authed_client)
    _create_job(authed_client, template["template_id"])

    other = _other_client(second_recruiter)
    response = other.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    assert response.json()["total_jobs"] == 0
