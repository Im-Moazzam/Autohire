from fastapi.testclient import TestClient

from app.api import fixtures


def test_list_templates(authed_client: TestClient) -> None:
    response = authed_client.get("/api/v1/templates")
    assert response.status_code == 200
    assert response.json()["total"] == len(fixtures.TEMPLATES)


def test_get_template(authed_client: TestClient) -> None:
    response = authed_client.get(f"/api/v1/templates/{fixtures.TEMPLATE_1_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["template_id"] == str(fixtures.TEMPLATE_1_ID)
    assert len(body["fields"]) >= 1


def test_create_template(authed_client: TestClient) -> None:
    response = authed_client.post(
        "/api/v1/templates",
        json={
            "template_name": "New Template",
            "fields": [
                {
                    "field_label": "Portfolio URL",
                    "field_type": "SHORT_TEXT",
                    "is_required": True,
                    "field_order": 1,
                }
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["template_name"] == "New Template"


def test_put_template_keeps_existing_field_id(authed_client: TestClient) -> None:
    response = authed_client.put(
        f"/api/v1/templates/{fixtures.TEMPLATE_1_ID}",
        json={
            "template_name": "Standard Software Role (revised)",
            "fields": [
                {
                    "field_id": str(fixtures.FIELD_NAME_ID),
                    "field_label": "Years of experience",
                    "field_type": "NUMBER",
                    "is_required": True,
                    "field_order": 1,
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fields"][0]["field_id"] == str(fixtures.FIELD_NAME_ID)


def test_delete_template_in_use_by_live_job_is_409(authed_client: TestClient) -> None:
    response = authed_client.delete(f"/api/v1/templates/{fixtures.TEMPLATE_1_ID}")
    assert response.status_code == 409
    assert response.json()["code"] == "TEMPLATE_IN_USE"


def test_delete_template_not_in_use(authed_client: TestClient) -> None:
    response = authed_client.delete(f"/api/v1/templates/{fixtures.TEMPLATE_2_ID}")
    assert response.status_code == 204
