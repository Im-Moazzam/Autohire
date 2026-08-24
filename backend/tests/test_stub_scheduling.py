import uuid

from fastapi.testclient import TestClient

# GET/PUT /scheduling/preferences moved to test_scheduling_preferences.py (US-24).
# GET /scheduling/available-slots, POST/GET /interviews moved to
# test_interviews.py (US-26) — they're real now, not a stub.
# PATCH /interviews/{slot_id} (reschedule/cancel) is genuinely Phase 2 and
# now returns an honest 501 instead of a fixture-backed 200 (TS-06/R-04) —
# see test_interviews.py::test_patch_real_slot_is_501_not_implemented for the
# full repro against a real slot.


def test_patch_interview_slot_is_501_not_implemented(authed_client: TestClient) -> None:
    response = authed_client.patch(
        f"/api/v1/interviews/{uuid.uuid4()}", json={"status": "CANCELLED"}
    )
    assert response.status_code == 501
    assert response.json()["code"] == "NOT_IMPLEMENTED"
