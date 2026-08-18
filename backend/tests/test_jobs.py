import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.resume_store import LocalResumeStore, get_resume_store
from app.api import fixtures
from app.main import app
from app.models.candidate import Candidate
from app.models.job import JobPosting
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
                {
                    "field_label": "Years of experience",
                    "field_type": "NUMBER",
                    "is_required": True,
                    "field_order": 2,
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _job_payload(template_id: str, title: str = "New Role") -> dict:
    return {
        "job_title": title,
        "job_description": "Own the API layer.",
        "template_id": template_id,
        "expires_at": "2027-01-01T00:00:00Z",
    }


def _create_job(client: TestClient, template_id: str, title: str = "New Role") -> dict:
    response = client.post("/api/v1/jobs", json=_job_payload(template_id, title))
    assert response.status_code == 201, response.text
    return response.json()


def _other_client(recruiter: Recruiter) -> TestClient:
    other = TestClient(app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other


# TC-01
def test_create_job_returns_live_with_slug_and_folder(authed_client: TestClient) -> None:
    template = _create_template(authed_client)
    body = _create_job(authed_client, template["template_id"])
    assert body["status"] == "LIVE"
    assert body["apply_slug"]
    assert body["google_drive_folder_id"]
    assert body["apply_url"] == f"http://localhost:5173/apply/{body['apply_slug']}"


# TC-02
def test_expires_at_in_past_is_422_no_row(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    payload = _job_payload(template["template_id"])
    payload["expires_at"] = "2020-01-01T00:00:00Z"
    response = authed_client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    assert db_session.query(JobPosting).count() == 0


# TC-03
def test_create_job_with_other_recruiters_template_is_404(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    other = _other_client(second_recruiter)
    other_template = _create_template(other, "Other's template")

    response = authed_client.post("/api/v1/jobs", json=_job_payload(other_template["template_id"]))
    assert response.status_code == 404
    assert response.json()["code"] == "TEMPLATE_NOT_FOUND"
    assert db_session.query(JobPosting).count() == 0


# TC-04
def test_create_job_with_soft_deleted_template_is_404(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    delete_response = authed_client.delete(f"/api/v1/templates/{template['template_id']}")
    assert delete_response.status_code == 204

    response = authed_client.post("/api/v1/jobs", json=_job_payload(template["template_id"]))
    assert response.status_code == 404
    assert db_session.query(JobPosting).count() == 0


# TC-05
def test_folder_creation_failure_leaves_draft_and_retry_keeps_slug(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)

    class _RaisingStore:
        def create_job_folder(self, recruiter: object, job_id: object, name: str) -> str:
            raise RuntimeError("disk full")

    app.dependency_overrides[get_resume_store] = lambda: _RaisingStore()
    try:
        response = authed_client.post("/api/v1/jobs", json=_job_payload(template["template_id"]))
    finally:
        app.dependency_overrides.pop(get_resume_store, None)

    # APP_ENV=local in tests: our own filesystem failed, not an upstream (502
    # is reserved for a real Drive failure in cloud mode).
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "RESUME_FOLDER_FAILED"
    job_id = uuid.UUID(body["details"]["job_id"])

    row = db_session.get(JobPosting, job_id)
    assert row is not None
    assert row.status == "DRAFT"
    assert row.google_drive_folder_id is None
    original_slug = row.apply_slug

    app.dependency_overrides[get_resume_store] = lambda: LocalResumeStore()
    try:
        retry = authed_client.patch(f"/api/v1/jobs/{job_id}", json={"status": "LIVE"})
    finally:
        app.dependency_overrides.pop(get_resume_store, None)

    assert retry.status_code == 200, retry.text
    retry_body = retry.json()
    assert retry_body["status"] == "LIVE"
    assert retry_body["google_drive_folder_id"]
    # The retry must not mint a new slug — a link shared from the failed
    # attempt would otherwise silently die.
    assert retry_body["apply_slug"] == original_slug
    assert db_session.query(JobPosting).count() == 1


# TC-06
def test_two_jobs_have_different_slugs(authed_client: TestClient) -> None:
    template = _create_template(authed_client)
    first = _create_job(authed_client, template["template_id"], "Role A")
    second = _create_job(authed_client, template["template_id"], "Role B")
    assert first["apply_slug"] != second["apply_slug"]


# TC-07
def test_slug_collision_is_retried(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    first = _create_job(authed_client, template["template_id"], "Role A")
    colliding_slug = first["apply_slug"]

    with patch(
        "app.services.job_service._new_slug", side_effect=[colliding_slug, "fresh-unique-slug"]
    ):
        response = authed_client.post(
            "/api/v1/jobs", json=_job_payload(template["template_id"], "Role B")
        )

    assert response.status_code == 201, response.text
    assert response.json()["apply_slug"] == "fresh-unique-slug"
    assert db_session.query(JobPosting).filter_by(apply_slug=colliding_slug).count() == 1


# TC-08
def test_get_another_recruiters_job_is_404(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])

    other = _other_client(second_recruiter)
    response = other.get(f"/api/v1/jobs/{job['job_id']}")
    assert response.status_code == 404


# TC-09
def test_patch_close_sets_closed_and_stops_accepting(authed_client: TestClient) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])

    response = authed_client.patch(f"/api/v1/jobs/{job['job_id']}", json={"status": "CLOSED"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CLOSED"
    assert body["is_accepting_responses"] is False


# TC-12
def test_list_jobs_only_returns_callers_jobs(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    template = _create_template(authed_client)
    _create_job(authed_client, template["template_id"])

    other = _other_client(second_recruiter)
    response = other.get("/api/v1/jobs")
    assert response.status_code == 200
    assert response.json()["total"] == 0


# STUB tests for US-15/US-16 process endpoints, moved from test_stub_jobs.py —
# they still need a real job row to exist, just in Postgres now.
def test_process_requires_closed_with_candidates(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.post(f"/api/v1/jobs/{fixtures.JOB_DRAFT_ID}/process")
    assert response.status_code == 409

    response = authed_client.post(f"/api/v1/jobs/{fixtures.JOB_CLOSED_ID}/process")
    assert response.status_code == 202
    body = response.json()
    assert body["task_id"]

    poll = authed_client.get(f"/api/v1/tasks/{body['task_id']}")
    assert poll.status_code == 200


def test_process_status_computed_counts(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.get(f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}/process/status")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == body["processed"] + body["failed"]
    assert body["failed"] >= 1


def _add_candidate(
    db_session: Session,
    job_id: uuid.UUID,
    email: str,
    status: str = "SUBMITTED",
    deleted: bool = False,
) -> Candidate:
    candidate = Candidate(
        job_id=job_id,
        full_name="Test Candidate",
        email=email,
        submission_status=status,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    db_session.add(candidate)
    db_session.commit()
    return candidate


# closes docs/drift.md row 29 — submission_count is a real COUNT, not a placeholder
def test_list_jobs_submission_count_reflects_real_candidates(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job_with_candidates = _create_job(authed_client, template["template_id"], "Role A")
    job_without = _create_job(authed_client, template["template_id"], "Role B")

    job_id = uuid.UUID(job_with_candidates["job_id"])
    _add_candidate(db_session, job_id, "one@example.com")
    _add_candidate(db_session, job_id, "two@example.com")
    _add_candidate(db_session, job_id, "soft-deleted@example.com", deleted=True)

    response = authed_client.get("/api/v1/jobs")
    assert response.status_code == 200
    by_id = {item["job_id"]: item for item in response.json()["items"]}
    assert by_id[job_with_candidates["job_id"]]["submission_count"] == 2
    assert by_id[job_without["job_id"]]["submission_count"] == 0


def test_job_detail_submission_counts_zero_filled_by_status(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    job_id = uuid.UUID(job["job_id"])
    _add_candidate(db_session, job_id, "submitted@example.com", status="SUBMITTED")
    _add_candidate(db_session, job_id, "parsed@example.com", status="PARSED")

    response = authed_client.get(f"/api/v1/jobs/{job['job_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["submission_count"] == 2
    assert body["submission_counts"]["SUBMITTED"] == 1
    assert body["submission_counts"]["PARSED"] == 1
    assert body["submission_counts"]["REJECTED"] == 0
