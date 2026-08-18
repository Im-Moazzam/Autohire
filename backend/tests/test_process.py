import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.enums import TaskStatus, TaskType
from app.services import task_service
from app.services.auth_service import SESSION_COOKIE, create_session_cookie


def _create_template(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/templates",
        json={
            "template_name": "Process Story Role",
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
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_closed_job(client: TestClient) -> dict:
    template = _create_template(client)
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Backend Engineer",
            "job_description": "Own the API layer.",
            "template_id": template["template_id"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    job = response.json()
    close = client.patch(f"/api/v1/jobs/{job['job_id']}", json={"status": "CLOSED"})
    assert close.status_code == 200, close.text
    return close.json()


def _add_candidate(db_session: Session, job_id: uuid.UUID, email: str) -> Candidate:
    # Commit 1 tests never run the real task body — no resume file is needed
    # on disk yet, just a candidate row so the has-candidates guard passes.
    candidate = Candidate(job_id=job_id, full_name=email.split("@")[0], email=email)
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def _get_recruiter(db_session: Session) -> Recruiter:
    return db_session.query(Recruiter).one()


def _mock_delay() -> Mock:
    return patch(
        "app.services.task_service.resume_parse_job.delay",
        return_value=Mock(id="fake-celery-id"),
    )


# TC-01
def test_trigger_returns_202_and_one_pending_task_row(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    _add_candidate(db_session, uuid.UUID(job["job_id"]), "a@example.com")

    with _mock_delay():
        response = authed_client.post(f"/api/v1/jobs/{job['job_id']}/process")

    assert response.status_code == 202
    body = response.json()
    assert body["task_type"] == "RESUME_PARSE"
    assert body["status"] == "PENDING"
    rows = db_session.query(BackgroundTask).filter_by(job_id=uuid.UUID(job["job_id"])).all()
    assert len(rows) == 1
    assert rows[0].status == TaskStatus.PENDING


# TC-02
def test_retrigger_while_pending_is_409_still_one_task(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    _add_candidate(db_session, uuid.UUID(job["job_id"]), "a@example.com")

    with _mock_delay():
        first = authed_client.post(f"/api/v1/jobs/{job['job_id']}/process")
        assert first.status_code == 202
        second = authed_client.post(f"/api/v1/jobs/{job['job_id']}/process")

    assert second.status_code == 409
    assert second.json()["code"] == "PROCESSING_IN_PROGRESS"
    rows = db_session.query(BackgroundTask).filter_by(job_id=uuid.UUID(job["job_id"])).all()
    assert len(rows) == 1


# TC-03
def test_trigger_on_job_with_no_candidates_is_409_no_task(authed_client: TestClient) -> None:
    job = _create_closed_job(authed_client)

    with _mock_delay():
        response = authed_client.post(f"/api/v1/jobs/{job['job_id']}/process")

    assert response.status_code == 409
    assert response.json()["code"] == "NO_CANDIDATES"


# TC-11
def test_trigger_on_another_recruiters_job_is_404(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    other = TestClient(authed_client.app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(second_recruiter.recruiter_id)))

    with _mock_delay():
        response = other.post(f"/api/v1/jobs/{job['job_id']}/process")

    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"


def test_not_closed_job_is_409_invalid_state(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    response = authed_client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Still Live",
            "job_description": "x",
            "template_id": template["template_id"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    job = response.json()
    _add_candidate(db_session, uuid.UUID(job["job_id"]), "a@example.com")

    with _mock_delay():
        response = authed_client.post(f"/api/v1/jobs/{job['job_id']}/process")

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"


def test_enqueue_writes_pending_row_before_delay_even_if_delay_raises(
    authed_client: TestClient, db_session: Session
) -> None:
    """The AC: background_tasks is written on enqueue, not on worker start —
    a worker/broker that never picks the job up still leaves a trace."""
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    _add_candidate(db_session, job_id, "a@example.com")
    recruiter = _get_recruiter(db_session)
    job_row = db_session.get(JobPosting, job_id)
    assert job_row is not None

    with (
        patch(
            "app.services.task_service.resume_parse_job.delay",
            side_effect=RuntimeError("broker down"),
        ),
        pytest.raises(RuntimeError),
    ):
        task_service.enqueue_resume_parse(db_session, recruiter, job_row)

    row = db_session.query(BackgroundTask).filter_by(job_id=job_id).one()
    assert row.status == TaskStatus.PENDING


def test_unique_index_backstops_concurrent_enqueue(
    authed_client: TestClient, db_session: Session
) -> None:
    """The pre-check is a fast path only — the partial unique index is the
    real guard. Insert a conflicting active row directly (bypassing the
    pre-check entirely) and confirm enqueue still can't create a second one."""
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    _add_candidate(db_session, job_id, "a@example.com")
    recruiter = _get_recruiter(db_session)

    winner = BackgroundTask(
        recruiter_id=recruiter.recruiter_id,
        job_id=job_id,
        task_type=TaskType.RESUME_PARSE,
        status=TaskStatus.RUNNING,
    )
    db_session.add(winner)
    db_session.commit()

    job_row = db_session.get(JobPosting, job_id)
    assert job_row is not None

    # Force the pre-check to miss (simulating the race window) so the test
    # proves the DB constraint, not the Python-level read-then-insert check.
    with (
        patch("app.services.task_service.active_task_for_job", return_value=None),
        pytest.raises(HTTPException) as exc_info,
    ):
        task_service.enqueue_resume_parse(db_session, recruiter, job_row)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "PROCESSING_IN_PROGRESS"
    rows = db_session.query(BackgroundTask).filter_by(job_id=job_id).all()
    assert len(rows) == 1


# TC-10
def test_process_status_sums_correctly_across_mixed_statuses(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    for status_, email in [
        ("SUBMITTED", "s@example.com"),
        ("PARSED", "p@example.com"),
        ("PARSE_ERROR", "e@example.com"),
        ("RANKED", "r@example.com"),
    ]:
        candidate = Candidate(job_id=job_id, full_name="x", email=email, submission_status=status_)
        db_session.add(candidate)
    db_session.commit()

    counts = task_service.process_status_for_job(db_session, job_id)
    assert counts["total"] == 4
    assert counts["failed"] == 1
    assert counts["processed"] == 2  # PARSED + RANKED
    assert counts["total"] == counts["processed"] + counts["failed"] + 1  # +1 SUBMITTED

    response = authed_client.get(f"/api/v1/jobs/{job['job_id']}/process/status")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["processed"] == 2
    assert body["failed"] == 1


def test_task_placeholder_run_marks_success_idempotently(
    authed_client: TestClient, db_session: Session
) -> None:
    """Commit 1's task body does no real extraction yet — this only proves
    the plumbing round-trip (PENDING -> RUNNING -> SUCCESS) and that running
    the same task_id twice is a safe no-op (TC-07's shape, ahead of commit 2's
    real per-candidate work)."""
    from app.tasks.resume_parse import resume_parse_job

    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id, job_id=job_id, task_type=TaskType.RESUME_PARSE
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    resume_parse_job.run(str(task.task_id))
    db_session.expire_all()
    db_session.refresh(task)
    assert task.status == TaskStatus.SUCCESS
    first_completed_at = task.completed_at

    resume_parse_job.run(str(task.task_id))
    db_session.expire_all()
    db_session.refresh(task)
    assert task.completed_at == first_completed_at
