from fastapi.testclient import TestClient

from app.api import fixtures

# GET/PUT /scheduling/preferences moved to test_scheduling_preferences.py (US-24).
# GET /scheduling/available-slots, POST/GET /interviews moved to
# test_interviews.py (US-26) — they're real now, not a stub. Only
# PATCH /interviews/{slot_id} (reschedule/cancel) is still a stub (Phase 2).


def test_patch_interview_slot_cancel(authed_client: TestClient) -> None:
    response = authed_client.patch(
        f"/api/v1/interviews/{fixtures.SLOT_PENDING_ID}", json={"status": "CANCELLED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
