import uuid

from fastapi.testclient import TestClient

from app.api import fixtures
from app.api.deps import get_current_recruiter
from app.api.routes.public import router as public_router
from app.models.job import JobPosting

ERROR_KEYS = {"code", "message", "details"}


def test_tc01_list_endpoint_default_page(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.get("/api/v1/jobs")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "size"}
    assert body["items"] != []
    assert body["page"] == 1
    assert body["size"] == 20


def test_tc02_list_endpoint_size_one(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.get("/api/v1/jobs", params={"size": 1})
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 1
    assert body["total"] == len(fixtures.JOBS)


def test_tc03_private_route_without_cookie_is_401_errorout(client: TestClient) -> None:
    response = client.get("/api/v1/jobs")
    assert response.status_code == 401
    body = response.json()
    assert set(body.keys()) == ERROR_KEYS
    assert body["code"] == "NOT_AUTHENTICATED"


def test_tc10_update_schema_unknown_field_is_422(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.patch(
        f"/api/v1/jobs/{fixtures.JOB_LIVE_ID}", json={"not_a_real_field": "x"}
    )
    assert response.status_code == 422
    body = response.json()
    assert set(body.keys()) == ERROR_KEYS
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["errors"]


def test_tc11_unknown_job_id_is_404_not_403(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == ERROR_KEYS
    assert body["code"] == "JOB_NOT_FOUND"


def test_409_error_matches_errorout_shape(
    authed_client: TestClient, seeded_stub_jobs: list[JobPosting]
) -> None:
    response = authed_client.patch(
        f"/api/v1/jobs/{fixtures.JOB_DRAFT_ID}", json={"status": "PROCESSED"}
    )
    assert response.status_code == 409
    body = response.json()
    assert set(body.keys()) == ERROR_KEYS
    assert body["code"] == "INVALID_STATE_TRANSITION"


def test_public_router_has_no_auth_dependency() -> None:
    """ADR-004 P1 / P7: the public apply router must never carry
    get_current_recruiter, on the router or on any individual route."""
    assert public_router.dependencies == []
    for route in public_router.routes:
        dependant = route.dependant
        assert dependant.call is not get_current_recruiter
        assert all(sub.call is not get_current_recruiter for sub in dependant.dependencies)
