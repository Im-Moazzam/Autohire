from fastapi.testclient import TestClient


def test_tc04_public_route_without_cookie_is_200(client: TestClient) -> None:
    response = client.get("/api/v1/public/apply/live-slug")
    assert response.status_code == 200


def test_tc05_unknown_slug_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/public/apply/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"


def test_tc06_expired_slug_is_410(client: TestClient) -> None:
    response = client.get("/api/v1/public/apply/expired-slug")
    assert response.status_code == 410
    assert response.json()["code"] == "JOB_EXPIRED"


def test_tc07_paused_slug_is_410(client: TestClient) -> None:
    response = client.get("/api/v1/public/apply/paused-slug")
    assert response.status_code == 410
    assert response.json()["code"] == "JOB_NOT_ACCEPTING"


def test_tc13_public_job_out_leaks_nothing_internal(client: TestClient) -> None:
    response = client.get("/api/v1/public/apply/live-slug")
    body = response.json()
    for leaked_key in (
        "job_id",
        "recruiter_id",
        "template_id",
        "submission_count",
        "submission_counts",
    ):
        assert leaked_key not in body


def test_submit_application_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/public/apply/live-slug",
        files={"resume": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["message"]
    assert "candidate_id" not in body
