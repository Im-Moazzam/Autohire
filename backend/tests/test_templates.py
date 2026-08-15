import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.recruiter import Recruiter
from app.models.template import FormTemplate
from app.services.auth_service import SESSION_COOKIE, create_session_cookie


def _mixed_fields() -> list[dict]:
    return [
        {
            "field_label": "Years of experience",
            "field_type": "NUMBER",
            "is_required": True,
            "field_order": 0,
        },
        {
            "field_label": "Why this role?",
            "field_type": "PARAGRAPH",
            "is_required": True,
            "field_order": 1,
        },
        {
            "field_label": "Preferred seniority",
            "field_type": "DROPDOWN",
            "is_required": False,
            "field_order": 2,
            "options": ["Junior", "Mid", "Senior"],
        },
        {
            "field_label": "Resume",
            "field_type": "FILE_UPLOAD",
            "is_required": True,
            "field_order": 3,
        },
    ]


def _create(client: TestClient, name: str, fields: list[dict] | None = None) -> dict:
    response = client.post(
        "/api/v1/templates",
        json={"template_name": name, "fields": fields if fields is not None else _mixed_fields()},
    )
    assert response.status_code == 201, response.text
    return response.json()


# TC-01
def test_create_template_with_mixed_fields_persists_in_order(authed_client: TestClient) -> None:
    body = _create(authed_client, "Standard Software Role")
    labels = [f["field_label"] for f in body["fields"]]
    assert labels == ["Years of experience", "Why this role?", "Preferred seniority", "Resume"]
    assert [f["field_order"] for f in body["fields"]] == [0, 1, 2, 3]

    refetched = authed_client.get(f"/api/v1/templates/{body['template_id']}")
    assert refetched.status_code == 200
    assert [f["field_label"] for f in refetched.json()["fields"]] == labels


# TC-02
def test_create_template_duplicate_name_is_409(authed_client: TestClient) -> None:
    _create(authed_client, "Internship")
    response = authed_client.post(
        "/api/v1/templates",
        json={"template_name": "Internship", "fields": _mixed_fields()},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "DUPLICATE_TEMPLATE_NAME"


# TC-03
def test_create_template_duplicate_name_after_soft_delete_is_free(
    authed_client: TestClient,
) -> None:
    first = _create(authed_client, "Internship")
    delete_response = authed_client.delete(f"/api/v1/templates/{first['template_id']}")
    assert delete_response.status_code == 204

    second = _create(authed_client, "Internship")
    assert second["template_id"] != first["template_id"]


# TC-04
def test_create_dropdown_field_without_options_is_422(
    authed_client: TestClient, db_session: Session
) -> None:
    for options in ([], None):
        fields = [
            {
                "field_label": "Preferred seniority",
                "field_type": "DROPDOWN",
                "is_required": False,
                "field_order": 0,
                **({"options": options} if options is not None else {}),
            }
        ]
        response = authed_client.post(
            "/api/v1/templates", json={"template_name": f"Bad {options}", "fields": fields}
        )
        assert response.status_code == 422

    assert db_session.query(FormTemplate).count() == 0


# TC-05
def test_create_text_field_with_options_is_422(authed_client: TestClient) -> None:
    fields = [
        {
            "field_label": "Portfolio URL",
            "field_type": "SHORT_TEXT",
            "is_required": True,
            "field_order": 0,
            "options": ["a"],
        }
    ]
    response = authed_client.post(
        "/api/v1/templates", json={"template_name": "Bad text", "fields": fields}
    )
    assert response.status_code == 422


# TC-06
def test_put_replacing_four_fields_with_two_leaves_exactly_two(authed_client: TestClient) -> None:
    created = _create(authed_client, "Standard Software Role")
    response = authed_client.put(
        f"/api/v1/templates/{created['template_id']}",
        json={
            "template_name": "Standard Software Role (revised)",
            "fields": [
                {
                    "field_label": "Portfolio URL",
                    "field_type": "SHORT_TEXT",
                    "is_required": True,
                    "field_order": 0,
                },
                {
                    "field_label": "Years of experience",
                    "field_type": "NUMBER",
                    "is_required": True,
                    "field_order": 1,
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["fields"]) == 2
    assert [f["field_order"] for f in body["fields"]] == [0, 1]


# TC-07
def test_field_orders_are_normalized_to_zero_based_sequence(authed_client: TestClient) -> None:
    fields = [
        {"field_label": "A", "field_type": "SHORT_TEXT", "field_order": 5},
        {"field_label": "B", "field_type": "SHORT_TEXT", "field_order": 10},
        {"field_label": "C", "field_type": "SHORT_TEXT", "field_order": 20},
    ]
    body = _create(authed_client, "Ordered", fields)
    assert [f["field_order"] for f in body["fields"]] == [0, 1, 2]
    assert [f["field_label"] for f in body["fields"]] == ["A", "B", "C"]


# TC-08
def test_get_another_recruiters_template_is_404(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    created = _create(authed_client, "Standard Software Role")

    other_client = TestClient(app)
    other_client.cookies.set(
        SESSION_COOKIE, create_session_cookie(str(second_recruiter.recruiter_id))
    )
    response = other_client.get(f"/api/v1/templates/{created['template_id']}")
    assert response.status_code == 404


# TC-09
def test_delete_then_get_is_404_but_row_survives_with_deleted_at(
    authed_client: TestClient, db_session: Session
) -> None:
    created = _create(authed_client, "Standard Software Role")
    template_id = uuid.UUID(created["template_id"])

    delete_response = authed_client.delete(f"/api/v1/templates/{template_id}")
    assert delete_response.status_code == 204

    get_response = authed_client.get(f"/api/v1/templates/{template_id}")
    assert get_response.status_code == 404

    row = db_session.get(FormTemplate, template_id)
    assert row is not None
    assert row.deleted_at is not None


# TC-10
def test_bad_field_in_create_leaves_no_template_row(
    authed_client: TestClient, db_session: Session
) -> None:
    fields = _mixed_fields()
    fields[1]["field_label"] = "x" * 300  # exceeds VARCHAR(200) — fails at flush, not Pydantic

    response = authed_client.post(
        "/api/v1/templates", json={"template_name": "Doomed", "fields": fields}
    )
    assert response.status_code == 500
    assert response.json()["code"] == "TEMPLATE_WRITE_FAILED"
    assert db_session.query(FormTemplate).count() == 0

    # session wasn't left poisoned by the failed transaction
    follow_up = authed_client.post(
        "/api/v1/templates", json={"template_name": "Fine", "fields": _mixed_fields()}
    )
    assert follow_up.status_code == 201


def test_list_templates_only_returns_callers_templates(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    _create(authed_client, "Mine")

    other_client = TestClient(app)
    other_client.cookies.set(
        SESSION_COOKIE, create_session_cookie(str(second_recruiter.recruiter_id))
    )
    response = other_client.get("/api/v1/templates")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_put_keeps_existing_field_id(authed_client: TestClient) -> None:
    created = _create(authed_client, "Standard Software Role")
    kept_field_id = created["fields"][0]["field_id"]

    response = authed_client.put(
        f"/api/v1/templates/{created['template_id']}",
        json={
            "template_name": "Standard Software Role (revised)",
            "fields": [
                {
                    "field_id": kept_field_id,
                    "field_label": "Years of experience (revised)",
                    "field_type": "NUMBER",
                    "is_required": True,
                    "field_order": 0,
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["fields"][0]["field_id"] == kept_field_id
