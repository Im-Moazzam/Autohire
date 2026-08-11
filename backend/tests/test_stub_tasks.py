import uuid

from fastapi.testclient import TestClient

from app.api import fixtures


def test_get_task(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/tasks/{fixtures.TASK_SUCCESS_ID}")
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"


def test_get_unknown_task_is_404(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/tasks/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "TASK_NOT_FOUND"
