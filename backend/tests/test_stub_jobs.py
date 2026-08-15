from fastapi.testclient import TestClient

from app.api import fixtures


def test_list_jobs_filter_by_status(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/jobs", params={"status": "DRAFT"})
    assert response.status_code == 200
    body = response.json()
    assert all(item["status"] == "DRAFT" for item in body["items"])
    assert body["total"] == 1


def test_get_job_detail_has_computed_apply_url_and_counts(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["apply_url"] == f"http://localhost:5173/apply/{body['apply_slug']}"
    assert "submission_counts" in body
    assert sum(body["submission_counts"].values()) == body["submission_count"]


def test_create_job(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/jobs",
        json={
            "job_title": "New Role",
            "job_description": "Desc",
            "template_id": str(fixtures.TEMPLATE_1_ID),
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201
    assert response.json()["job_title"] == "New Role"


def test_close_job_is_patch_status(authed_client: TestClient) -> None:
    response = authed_client.patch(
        f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}", json={"status": "CLOSED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"


def test_illegal_transition_is_409(authed_client: TestClient) -> None:
    response = authed_client.patch(
        f"/api/v1/jobs/{fixtures.JOB_DRAFT_ID}", json={"status": "CLOSED"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"


def test_process_requires_closed_with_candidates(authed_client: TestClient) -> None:
    response = authed_client.post(f"/api/v1/jobs/{fixtures.JOB_DRAFT_ID}/process")
    assert response.status_code == 409

    response = authed_client.post(f"/api/v1/jobs/{fixtures.JOB_CLOSED_ID}/process")
    assert response.status_code == 202
    body = response.json()
    assert body["task_id"]

    poll = authed_client.get(f"/api/v1/tasks/{body['task_id']}")
    assert poll.status_code == 200


def test_process_status_computed_counts(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}/process/status")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == body["processed"] + body["failed"]
    assert body["failed"] >= 1
