from fastapi.testclient import TestClient

from app.api import fixtures


def test_send_email_returns_task(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/emails/send",
        json={
            "email_type": "INTERVIEW_INVITE",
            "candidate_ids": [str(fixtures.CANDIDATE_RANKED_1_ID)],
        },
    )
    assert response.status_code == 202
    assert response.json()["task_id"]


def test_list_emails_includes_failed_delivery(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/emails")
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["delivery_status"] == "FAILED" for item in items)
    assert all("candidate_name" in item for item in items)


def test_list_emails_filter_by_job(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/emails", params={"job_id": str(fixtures.JOB_LIVE_ID)})
    assert response.status_code == 200
    assert response.json()["total"] >= 1
