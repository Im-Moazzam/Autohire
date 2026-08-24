from fastapi.testclient import TestClient

# GET /emails moved to test_emails.py (US-27) — it's real now, not a stub.
# POST /emails/send (manual, ad hoc send) is genuinely Phase 2 and now returns
# an honest 501 instead of a stale fixture TaskOut (TS-06/R-04) — see
# test_emails.py::test_send_email_is_501_not_implemented for the full repro.


def test_send_email_is_501_not_implemented(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/emails/send",
        json={"email_type": "INTERVIEW_INVITE", "candidate_ids": []},
    )
    assert response.status_code == 501
    assert response.json()["code"] == "NOT_IMPLEMENTED"
