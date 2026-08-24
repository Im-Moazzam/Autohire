"""TS-06/R-05: GET /auth/me and PATCH /recruiters/me depend on
get_current_recruiter (so 401 is reachable at runtime — see
test_auth.py::test_tc05_me_without_cookie_is_401 and
test_recruiters.py::test_tc05_patch_without_session_cookie_is_401) but did
not declare 401 in responses=, so the generated client typed the 401 branch
frontend/src/lib/auth.ts relies on as unreachable."""

from fastapi.testclient import TestClient


def _declared_statuses(client: TestClient, path: str, method: str) -> set[str]:
    schema = client.get("/openapi.json").json()
    return set(schema["paths"][path][method]["responses"].keys())


def test_auth_me_declares_401(client: TestClient) -> None:
    assert "401" in _declared_statuses(client, "/api/v1/auth/me", "get")


def test_recruiters_me_patch_declares_401(client: TestClient) -> None:
    assert "401" in _declared_statuses(client, "/api/v1/recruiters/me", "patch")


# TS-06/R-06: job_service.finalize_launch raises 500 RESUME_FOLDER_FAILED when
# APP_ENV=local (the demo config) and 502 otherwise, but POST/PATCH /jobs only
# declared 502.
def test_jobs_post_declares_500(client: TestClient) -> None:
    assert "500" in _declared_statuses(client, "/api/v1/jobs", "post")


def test_jobs_patch_declares_500(client: TestClient) -> None:
    assert "500" in _declared_statuses(client, "/api/v1/jobs/{job_id}", "patch")
