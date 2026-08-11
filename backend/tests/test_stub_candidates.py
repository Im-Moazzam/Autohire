from fastapi.testclient import TestClient

from app.api import fixtures


def test_tc08_filter_by_parse_error(authed_client: TestClient) -> None:
    response = authed_client.get(
        f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}/candidates",
        params={"submission_status": "PARSE_ERROR"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert all(item["submission_status"] == "PARSE_ERROR" for item in body["items"])
    assert all(item["parse_error"] is not None for item in body["items"])


def test_ranked_candidates_are_sorted_and_scored(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}/candidates/ranked")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 2
    positions = [item["rank_position"] for item in body["items"]]
    assert positions == sorted(positions)
    assert all("semantic_score" in item for item in body["items"])


def test_candidate_detail_includes_typed_form_responses(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/candidates/{fixtures.CANDIDATE_RANKED_1_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["form_responses"]
    for fr in body["form_responses"]:
        assert fr["field_id"]
        assert fr["field_type"]


def test_unknown_candidate_is_404(authed_client: TestClient) -> None:
    import uuid

    response = authed_client.get(f"/api/v1/candidates/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "CANDIDATE_NOT_FOUND"


def test_patch_candidate_status(authed_client: TestClient) -> None:
    response = authed_client.patch(
        f"/api/v1/candidates/{fixtures.CANDIDATE_SUBMITTED_ID}",
        json={"submission_status": "REJECTED"},
    )
    assert response.status_code == 200
    assert response.json()["submission_status"] == "REJECTED"
