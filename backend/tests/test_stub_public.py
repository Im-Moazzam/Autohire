from fastapi.testclient import TestClient

from app.main import app
from app.models.job import JobPosting

# GET /public/apply/{slug} moved to tests/test_public_apply.py in US-11 — the
# route is real now, not fixture-backed, so it needed real job/template rows.


def test_submit_application_success(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    # STUB: US-12. authed_client is only needed to trigger seeded_stub_jobs'
    # setup dependency chain; the request itself goes through a bare,
    # cookieless client, matching how a candidate actually calls this route.
    response = TestClient(app).post(
        "/api/v1/public/apply/live-slug",
        files={"resume": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["message"]
    assert "candidate_id" not in body
