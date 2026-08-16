import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.job import JobPosting

_LEAKED_KEYS = {"job_id", "recruiter_id", "template_id", "submission_count", "apply_slug"}


def _create_template_with_dropdown(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/templates",
        json={
            "template_name": "Standard Software Role",
            "fields": [
                {
                    "field_label": "Years of experience",
                    "field_type": "NUMBER",
                    "is_required": True,
                    "field_order": 1,
                },
                {
                    "field_label": "Seniority",
                    "field_type": "DROPDOWN",
                    "is_required": True,
                    "field_order": 0,
                    "options": ["Junior", "Mid", "Senior"],
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_job(client: TestClient, template_id: str) -> dict:
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Senior Backend Engineer",
            "job_description": "Own the API layer.",
            "template_id": template_id,
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _walk_no_leaked_keys(node: object) -> None:
    """Recurses the full response body, not just top-level keys, so a leak
    nested inside `fields` (or anywhere else) is caught too."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert key not in _LEAKED_KEYS, f"leaked key: {key}"
            _walk_no_leaked_keys(value)
    elif isinstance(node, list):
        for item in node:
            _walk_no_leaked_keys(item)


# TC-01
def test_live_accepting_unexpired_returns_public_job(authed_client: TestClient) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_title"] == "Senior Backend Engineer"
    orders = [f["field_order"] for f in body["fields"]]
    assert orders == sorted(orders)
    dropdown = next(f for f in body["fields"] if f["field_type"] == "DROPDOWN")
    assert dropdown["options"] == ["Junior", "Mid", "Senior"]


# TC-02
def test_unknown_slug_is_404(authed_client: TestClient) -> None:
    response = TestClient(app).get("/api/v1/public/apply/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"


# TC-03
def test_soft_deleted_job_is_404_same_as_unknown(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])
    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.deleted_at = datetime.now(UTC)
    db_session.commit()

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    unknown = TestClient(app).get("/api/v1/public/apply/does-not-exist")
    assert response.status_code == 404
    assert response.json() == unknown.json()


# TC-04
def test_draft_job_is_404_same_as_unknown(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])
    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.status = "DRAFT"
    db_session.commit()

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    unknown = TestClient(app).get("/api/v1/public/apply/does-not-exist")
    assert response.status_code == 404
    assert response.json() == unknown.json()


# TC-05
def test_closed_job_is_410_job_closed_with_title(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])
    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.status = "CLOSED"
    db_session.commit()

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    assert response.status_code == 410
    body = response.json()
    assert body["code"] == "JOB_CLOSED"
    assert body["details"]["job_title"] == "Senior Backend Engineer"
    assert body["details"]["reason"] == "CLOSED"


# TC-06
def test_not_accepting_responses_is_410_paused(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])
    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.is_accepting_responses = False
    db_session.commit()

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    assert response.status_code == 410
    assert response.json()["details"]["reason"] == "PAUSED"


# TC-07
def test_expired_but_still_live_is_410_expired(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])
    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    assert row.status == "LIVE"

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    assert response.status_code == 410
    assert response.json()["details"]["reason"] == "EXPIRED"


# TC-08
def test_response_leaks_no_internal_fields(authed_client: TestClient) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])

    response = TestClient(app).get(f"/api/v1/public/apply/{job['apply_slug']}")
    body = response.json()
    _walk_no_leaked_keys(body)
    # field_id is intentionally allowed through — it's the FK key US-12 needs
    # for candidate_form_responses, not a tenant/job/recruiter identifier.
    assert all("field_id" in f for f in body["fields"])


# TC-09
def test_works_with_no_session_cookie(authed_client: TestClient) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])

    bare = TestClient(app)
    assert "cookie" not in {k.lower() for k in bare.headers}
    response = bare.get(f"/api/v1/public/apply/{job['apply_slug']}")
    assert response.status_code == 200


# TC-10
def test_draft_job_still_visible_to_owner(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template_with_dropdown(authed_client)
    job = _create_job(authed_client, template["template_id"])
    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.status = "DRAFT"
    db_session.commit()

    response = authed_client.get(f"/api/v1/jobs/{job['job_id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"
