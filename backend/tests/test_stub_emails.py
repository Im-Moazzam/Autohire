from fastapi.testclient import TestClient

from app.api import fixtures

# GET /emails moved to test_emails.py (US-27) — it's real now, not a stub.
# Only POST /emails/send (manual, ad hoc send) is still a stub — out of this
# story's scope, per docs/stories/US-26-27.md.


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
