import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.interview import InterviewSlot
from app.models.recruiter import Recruiter
from app.models.scheduling import SchedulingPreference
from app.schemas.enums import SlotStatus, SubmissionStatus, TaskStatus, TaskType
from app.services.auth_service import SESSION_COOKIE, create_session_cookie
from app.services.interview_service import generate_slots
from app.tasks.calendar_sync import calendar_sync_job

_PREFS_PAYLOAD = {
    "available_days": [
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        "SATURDAY",
        "SUNDAY",
    ],
    "available_start_time": "09:00:00",
    "available_end_time": "17:00:00",
    "slot_duration_minutes": 30,
}


def _other_client(recruiter: Recruiter) -> TestClient:
    other = TestClient(app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other


def _set_preferences(client: TestClient) -> None:
    response = client.put("/api/v1/scheduling/preferences", json=_PREFS_PAYLOAD)
    assert response.status_code == 200, response.text


def _create_job(client: TestClient) -> dict:
    template = client.post(
        "/api/v1/templates",
        json={
            "template_name": f"Scheduling Story Role {uuid.uuid4()}",
            "fields": [
                {
                    "field_label": "Email",
                    "field_type": "SHORT_TEXT",
                    "is_required": True,
                    "field_order": 0,
                },
                {
                    "field_label": "Full Name",
                    "field_type": "SHORT_TEXT",
                    "is_required": True,
                    "field_order": 1,
                },
            ],
        },
    ).json()
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Backend Engineer",
            "job_description": "Backend role needing python and sql.",
            "template_id": template["template_id"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_candidate(
    db_session: Session, job_id: uuid.UUID, email: str, status: str = "RANKED"
) -> Candidate:
    candidate = Candidate(
        job_id=job_id,
        full_name=email.split("@")[0],
        email=email,
        submission_status=status,
        submitted_at=datetime.now(UTC),
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def _get_recruiter(db_session: Session) -> Recruiter:
    return db_session.query(Recruiter).one()


def _make_task_row(db_session: Session, recruiter: Recruiter, job_id: uuid.UUID) -> BackgroundTask:
    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id, job_id=job_id, task_type=TaskType.CALENDAR_SYNC
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class _FakeCalendarStore:
    def create_event(self, recruiter, **kwargs):  # noqa: ANN001, ANN003
        return Mock(event_id=f"cal-{uuid.uuid4().hex}", meet_link="https://meet.local.test/fake")


def _patch_calendar_store():
    return patch("app.tasks.calendar_sync.get_calendar_store", return_value=_FakeCalendarStore())


def _no_op_email_dispatch():
    return patch("app.tasks.calendar_sync.email_dispatch_job.delay")


def _run_calendar_sync(
    db_session: Session, task: BackgroundTask, candidate_ids: list[uuid.UUID]
) -> None:
    with _patch_calendar_store(), _no_op_email_dispatch():
        calendar_sync_job.run(str(task.task_id), [str(cid) for cid in candidate_ids])
    db_session.expire_all()


# TC-01
def test_schedule_three_ranked_candidates(authed_client: TestClient, db_session: Session) -> None:
    _set_preferences(authed_client)
    job = _create_job(authed_client)
    recruiter = _get_recruiter(db_session)
    candidates = [_add_candidate(db_session, job["job_id"], f"c{i}@example.com") for i in range(3)]

    task = _make_task_row(db_session, recruiter, job["job_id"])
    _run_calendar_sync(db_session, task, [c.candidate_id for c in candidates])

    slots = db_session.query(InterviewSlot).all()
    assert len(slots) == 3
    times = {slot.scheduled_at for slot in slots}
    assert len(times) == 3  # distinct
    for slot in slots:
        assert slot.status == SlotStatus.PENDING
        assert slot.google_calendar_event_id is not None

    for candidate in candidates:
        db_session.refresh(candidate)
        assert candidate.submission_status == SubmissionStatus.INVITED

    db_session.refresh(task)
    assert task.status == TaskStatus.SUCCESS
    assert task.result_summary["scheduled"] == 3
    assert task.result_summary["unscheduled"] == []


# TC-02
def test_schedule_parse_error_candidate_is_422(
    authed_client: TestClient, db_session: Session
) -> None:
    _set_preferences(authed_client)
    job = _create_job(authed_client)
    candidate = _add_candidate(db_session, job["job_id"], "bad@example.com", status="PARSE_ERROR")

    response = authed_client.post(
        "/api/v1/interviews",
        json={"job_id": job["job_id"], "candidate_ids": [str(candidate.candidate_id)]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CANDIDATE_STATUS"
    assert db_session.query(InterviewSlot).count() == 0


# TC-03
def test_two_runs_for_same_candidate_leave_one_live_slot(
    authed_client: TestClient, db_session: Session
) -> None:
    _set_preferences(authed_client)
    job = _create_job(authed_client)
    recruiter = _get_recruiter(db_session)
    candidate = _add_candidate(db_session, job["job_id"], "once@example.com")

    task1 = _make_task_row(db_session, recruiter, job["job_id"])
    _run_calendar_sync(db_session, task1, [candidate.candidate_id])
    assert db_session.query(InterviewSlot).count() == 1

    # Candidate is now INVITED, not RANKED — re-running would 422 through the
    # route, so drive the task directly to prove the constraint itself holds
    # even if a candidate's status were (incorrectly) still RANKED on retry.
    db_session.refresh(candidate)
    candidate.submission_status = SubmissionStatus.RANKED
    db_session.commit()

    task2 = _make_task_row(db_session, recruiter, job["job_id"])
    _run_calendar_sync(db_session, task2, [candidate.candidate_id])

    live = (
        db_session.query(InterviewSlot)
        .filter(InterviewSlot.status.in_([SlotStatus.PENDING, SlotStatus.CONFIRMED]))
        .all()
    )
    assert len(live) == 1
    db_session.refresh(task2)
    assert task2.result_summary["unscheduled"][0]["reason"] == "ALREADY_SCHEDULED"


# TC-04
def test_more_candidates_than_slots_reports_the_rest(
    authed_client: TestClient, db_session: Session
) -> None:
    _set_preferences(authed_client)
    job = _create_job(authed_client)
    recruiter = _get_recruiter(db_session)
    candidates = [
        _add_candidate(db_session, job["job_id"], f"tc04-{i}@example.com") for i in range(5)
    ]

    task = _make_task_row(db_session, recruiter, job["job_id"])

    # Simulate exactly 2 slots of real capacity, independent of wall-clock
    # date/weekday — TC-10/TC-11/TC-11b already prove generate_slots' real
    # calendar math directly; this test proves the task's scarcity handling.
    def _capped(pref, occupied, count, now, horizon_days=14):  # noqa: ANN001
        if len(occupied) >= 2:
            return []
        return [now + timedelta(hours=1 + len(occupied))]

    with (
        patch("app.tasks.calendar_sync.generate_slots", side_effect=_capped),
        _patch_calendar_store(),
        _no_op_email_dispatch(),
    ):
        calendar_sync_job.run(str(task.task_id), [str(c.candidate_id) for c in candidates])

    db_session.refresh(task)
    assert task.status == TaskStatus.SUCCESS
    assert task.result_summary["scheduled"] == 2
    unscheduled = task.result_summary["unscheduled"]
    assert len(unscheduled) == 3
    assert all(item["reason"] == "NO_SLOT_IN_HORIZON" for item in unscheduled)
    assert all(item["full_name"] for item in unscheduled)  # names present, not silently dropped
    scheduled_ids = {str(c.candidate_id) for c in candidates} - {
        item["candidate_id"] for item in unscheduled
    }
    assert len(scheduled_ids) == 2


# TC-05
def test_calendar_failure_leaves_slot_without_event_id(
    authed_client: TestClient, db_session: Session
) -> None:
    _set_preferences(authed_client)
    job = _create_job(authed_client)
    recruiter = _get_recruiter(db_session)
    candidate = _add_candidate(db_session, job["job_id"], "cal-fail@example.com")

    task = _make_task_row(db_session, recruiter, job["job_id"])
    failing_store = Mock(create_event=Mock(side_effect=RuntimeError("calendar down")))
    with (
        patch("app.tasks.calendar_sync.get_calendar_store", return_value=failing_store),
        _no_op_email_dispatch() as mock_dispatch,
    ):
        calendar_sync_job.run(str(task.task_id), [str(candidate.candidate_id)])

    slot = db_session.query(InterviewSlot).one()
    assert slot.google_calendar_event_id is None
    assert slot.status == SlotStatus.PENDING

    db_session.refresh(candidate)
    assert candidate.submission_status == SubmissionStatus.RANKED  # never INVITED with no interview

    mock_dispatch.assert_not_called()
    db_session.refresh(task)
    assert task.result_summary["unscheduled"][0]["reason"] == "CALENDAR_FAILED"


# TC-06
def test_no_scheduling_preferences_is_409(authed_client: TestClient, db_session: Session) -> None:
    job = _create_job(authed_client)
    candidate = _add_candidate(db_session, job["job_id"], "nopref@example.com")

    response = authed_client.post(
        "/api/v1/interviews",
        json={"job_id": job["job_id"], "candidate_ids": [str(candidate.candidate_id)]},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "NO_SCHEDULING_PREFERENCES"


# TC-09
def test_cross_tenant_schedule_is_404(
    authed_client: TestClient, db_session: Session, second_recruiter: Recruiter
) -> None:
    _set_preferences(authed_client)
    job = _create_job(authed_client)
    candidate = _add_candidate(db_session, job["job_id"], "xtenant@example.com")

    other = _other_client(second_recruiter)
    response = other.post(
        "/api/v1/interviews",
        json={"job_id": job["job_id"], "candidate_ids": [str(candidate.candidate_id)]},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"


def _pref(
    available_days: list[str],
    start: time,
    end: time,
    duration_minutes: int,
    timezone: str = "UTC",
) -> SchedulingPreference:
    # Transient — never added to a session; generate_slots only reads attrs.
    return SchedulingPreference(
        recruiter_id=uuid.uuid4(),
        available_days=available_days,
        available_start_time=start,
        available_end_time=end,
        slot_duration_minutes=duration_minutes,
        timezone=timezone,
    )


# TC-10
def test_generated_slots_respect_days_window_and_duration() -> None:
    pref = _pref(["MONDAY", "WEDNESDAY"], time(9, 0), time(11, 0), 30)
    now = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)  # a Monday

    slots = generate_slots(pref, occupied=[], count=10, now=now)

    assert slots
    for slot in slots:
        local = slot.astimezone(UTC)
        assert local.strftime("%A").upper() in {"MONDAY", "WEDNESDAY"}
        assert time(9, 0) <= local.time() < time(11, 0)
    # every slot 30 minutes apart within a day
    by_day: dict[date, list[datetime]] = {}
    for slot in slots:
        by_day.setdefault(slot.date(), []).append(slot)
    for times in by_day.values():
        times.sort()
        for a, b in zip(times, times[1:], strict=False):
            assert (b - a) == timedelta(minutes=30)


# TC-11
def test_existing_pending_slot_blocks_that_exact_time() -> None:
    pref = _pref(["MONDAY"], time(9, 0), time(10, 0), 30)
    now = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)  # a Monday
    first_slot_start = datetime(2026, 8, 24, 9, 0, tzinfo=UTC)
    occupied = [(first_slot_start, first_slot_start + timedelta(minutes=30))]

    slots = generate_slots(pref, occupied, count=1, now=now)

    assert slots
    assert slots[0] != first_slot_start
    assert slots[0] == first_slot_start + timedelta(minutes=30)


# TC-11b
def test_overlap_check_honours_existing_slots_own_duration() -> None:
    # An existing slot was booked at 09:00 for 60 minutes (a longer duration
    # than the preference now specifies) — a plain exact-timestamp check
    # would let a new 30-minute slot land at 09:30, inside the old slot.
    pref = _pref(["MONDAY"], time(9, 0), time(11, 0), 30)
    now = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    existing_start = datetime(2026, 8, 24, 9, 0, tzinfo=UTC)
    occupied = [(existing_start, existing_start + timedelta(minutes=60))]

    slots = generate_slots(pref, occupied, count=1, now=now)

    assert slots
    assert slots[0] == datetime(2026, 8, 24, 10, 0, tzinfo=UTC)


def test_generate_slots_uses_row_timezone_not_live_setting() -> None:
    # ADR-005: ZoneInfo(pref.timezone), never settings.scheduling_timezone —
    # even when the live setting has since changed to something else.
    pref = _pref(["MONDAY"], time(9, 0), time(10, 0), 30, timezone="Asia/Karachi")
    now = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)

    with patch("app.core.config.settings.scheduling_timezone", "America/New_York"):
        slots = generate_slots(pref, occupied=[], count=1, now=now)

    assert slots
    # 09:00 Asia/Karachi (UTC+5) == 04:00 UTC, not 09:00 America/New_York (UTC-4/-5).
    assert slots[0].astimezone(UTC).hour == 4
