from fastapi.testclient import TestClient

from app.api import fixtures

# GET/PUT /scheduling/preferences moved to test_scheduling_preferences.py (US-24) —
# they're real now, not a stub.


def test_available_slots_is_bare_list_not_paginated(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/scheduling/available-slots", params={"count": 2})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 2


def test_schedule_interviews_returns_task(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/interviews",
        json={
            "job_id": str(fixtures.JOB_LIVE_ID),
            "candidate_ids": [str(fixtures.CANDIDATE_RANKED_1_ID)],
        },
    )
    assert response.status_code == 202
    assert response.json()["task_id"]


def test_list_interviews_includes_cancelled_and_null_meet_link(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/interviews", params={"job_id": str(fixtures.JOB_LIVE_ID)})
    assert response.status_code == 200
    items = response.json()["items"]
    assert any(item["status"] == "CANCELLED" for item in items)
    assert any(item["google_meet_link"] is None for item in items)


def test_patch_interview_slot_cancel(authed_client: TestClient) -> None:
    response = authed_client.patch(
        f"/api/v1/interviews/{fixtures.SLOT_PENDING_ID}", json={"status": "CANCELLED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
