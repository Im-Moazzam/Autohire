from fastapi.testclient import TestClient

from app.api import fixtures
from app.models.job import JobPosting


# STUB: US-19 — ranked candidates are still fixture-backed until scoring lands.
def test_ranked_candidates_are_sorted_and_scored(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.get(f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}/candidates/ranked")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 2
    positions = [item["rank_position"] for item in body["items"]]
    assert positions == sorted(positions)
    assert all("semantic_score" in item for item in body["items"])
