import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import app
from app.models.recruiter import Recruiter
from app.models.scheduling import SchedulingPreference
from app.services.auth_service import SESSION_COOKIE, create_session_cookie

_VALID_PAYLOAD = {
    "available_days": ["MONDAY", "FRIDAY"],
    "available_start_time": "09:00:00",
    "available_end_time": "17:00:00",
    "slot_duration_minutes": 45,
}


def _other_client(recruiter: Recruiter) -> TestClient:
    other_client = TestClient(app)
    other_client.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other_client


# TC-03
def test_get_before_any_put_returns_synthesized_defaults(
    authed_client: TestClient, db_session: Session
) -> None:
    response = authed_client.get("/api/v1/scheduling/preferences")

    assert response.status_code == 200
    body = response.json()
    assert body["preference_id"] is None
    assert body["available_days"] == ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    assert body["available_start_time"] == "09:00:00"
    assert body["available_end_time"] == "17:00:00"
    assert body["slot_duration_minutes"] == 30
    assert body["last_synced_at"] is None
    # A GET must not write anything — synthesized, not persisted.
    assert db_session.query(SchedulingPreference).count() == 0


# TC-01
def test_first_put_creates_a_row(authed_client: TestClient, db_session: Session) -> None:
    response = authed_client.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["preference_id"] is not None
    assert body["available_days"] == ["MONDAY", "FRIDAY"]
    assert body["available_start_time"] == "09:00:00"
    assert body["available_end_time"] == "17:00:00"
    assert body["slot_duration_minutes"] == 45
    assert body["timezone"] == settings.scheduling_timezone
    assert db_session.query(SchedulingPreference).count() == 1


# TC-02
def test_second_put_updates_the_same_row(authed_client: TestClient, db_session: Session) -> None:
    first = authed_client.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD)
    first_id = first.json()["preference_id"]

    second = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={
            "available_days": ["TUESDAY"],
            "available_start_time": "10:00:00",
            "available_end_time": "12:00:00",
            "slot_duration_minutes": 30,
        },
    )

    assert second.status_code == 200
    body = second.json()
    assert body["preference_id"] == first_id
    assert body["available_days"] == ["TUESDAY"]
    assert body["slot_duration_minutes"] == 30
    assert db_session.query(SchedulingPreference).count() == 1


# TC-04
def test_put_rejects_inverted_window(authed_client: TestClient, db_session: Session) -> None:
    response = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={
            "available_days": ["MONDAY"],
            "available_start_time": "17:00:00",
            "available_end_time": "09:00:00",
            "slot_duration_minutes": 30,
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert db_session.query(SchedulingPreference).count() == 0


# TC-05
def test_put_rejects_empty_available_days(authed_client: TestClient, db_session: Session) -> None:
    response = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={**_VALID_PAYLOAD, "available_days": []},
    )

    assert response.status_code == 422
    assert db_session.query(SchedulingPreference).count() == 0


# TC-06
def test_put_rejects_unknown_day(authed_client: TestClient, db_session: Session) -> None:
    response = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={**_VALID_PAYLOAD, "available_days": ["Funday"]},
    )

    assert response.status_code == 422
    assert db_session.query(SchedulingPreference).count() == 0


# TC-07
def test_put_normalizes_mixed_case_and_dedupes_days(
    authed_client: TestClient, db_session: Session
) -> None:
    response = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={**_VALID_PAYLOAD, "available_days": ["monday", "MONDAY", "friday"]},
    )

    assert response.status_code == 200
    assert response.json()["available_days"] == ["MONDAY", "FRIDAY"]
    assert db_session.query(SchedulingPreference).count() == 1


# TC-08
def test_put_rejects_slot_duration_larger_than_window(
    authed_client: TestClient, db_session: Session
) -> None:
    response = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={
            "available_days": ["MONDAY"],
            "available_start_time": "09:00:00",
            "available_end_time": "10:00:00",
            "slot_duration_minutes": 90,
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert db_session.query(SchedulingPreference).count() == 0


def test_put_rejects_slot_duration_out_of_bounds(authed_client: TestClient) -> None:
    too_short = authed_client.put(
        "/api/v1/scheduling/preferences", json={**_VALID_PAYLOAD, "slot_duration_minutes": 5}
    )
    too_long = authed_client.put(
        "/api/v1/scheduling/preferences", json={**_VALID_PAYLOAD, "slot_duration_minutes": 240}
    )

    assert too_short.status_code == 422
    assert too_long.status_code == 422


# TC-09
def test_put_ignores_or_rejects_recruiter_id_in_body(
    authed_client: TestClient, db_session: Session
) -> None:
    response = authed_client.put(
        "/api/v1/scheduling/preferences",
        json={**_VALID_PAYLOAD, "recruiter_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 422
    assert db_session.query(SchedulingPreference).count() == 0


# TC-10
def test_another_recruiters_preferences_are_unreachable(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    authed_client.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD)

    other = _other_client(second_recruiter)
    other_get = other.get("/api/v1/scheduling/preferences")
    assert other_get.status_code == 200
    assert other_get.json()["preference_id"] is None  # sees defaults, not recruiter A's row

    other_put = other.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD)
    assert other_put.status_code == 200
    assert db_session.query(SchedulingPreference).count() == 2  # two independent rows


def test_get_and_put_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/scheduling/preferences").status_code == 401
    assert client.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD).status_code == 401


def test_get_after_put_returns_the_saved_row(authed_client: TestClient) -> None:
    authed_client.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD)

    response = authed_client.get("/api/v1/scheduling/preferences")

    assert response.status_code == 200
    body = response.json()
    assert body["preference_id"] is not None
    assert body["available_days"] == ["MONDAY", "FRIDAY"]
    assert body["timezone"] == settings.scheduling_timezone


def test_timezone_is_fixed_at_write_time_not_read_live(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    authed_client.put("/api/v1/scheduling/preferences", json=_VALID_PAYLOAD)

    monkeypatch.setattr(settings, "scheduling_timezone", "UTC")
    response = authed_client.get("/api/v1/scheduling/preferences")

    # The saved row keeps the zone it was written in, not the now-changed setting.
    assert response.json()["timezone"] != "UTC"
