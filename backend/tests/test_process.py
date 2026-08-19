import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.resume_store import local_job_folder
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.enums import TaskStatus, TaskType
from app.services import task_service
from app.services.auth_service import SESSION_COOKIE, create_session_cookie
from app.tasks.resume_parse import resume_parse_job

_FIXTURES = Path(__file__).parent / "fixtures" / "resumes"


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
    # Enqueue-path tests never run the real task body — no resume file is
    # needed on disk, just a candidate row so the has-candidates guard passes.
    candidate = Candidate(job_id=job_id, full_name=email.split("@")[0], email=email)
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def _add_candidate_with_resume(
    db_session: Session, job_id: uuid.UUID, email: str, fixture_name: str
) -> Candidate:
    ext = fixture_name.rsplit(".", 1)[-1]
    folder = local_job_folder(job_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{uuid.uuid4()}.{ext}"
    target.write_bytes((_FIXTURES / fixture_name).read_bytes())
    candidate = Candidate(
        job_id=job_id, full_name=email.split("@")[0], email=email, resume_storage_key=str(target)
    )
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


# --- transition graph --------------------------------------------------------


def test_patch_parsed_backwards_to_submitted_is_409(
    authed_client: TestClient, db_session: Session
) -> None:
    # Same-state PATCH (PARSED -> PARSED) is a legal no-op, mirroring
    # job_service.is_legal_transition. The illegal move is going backwards —
    # PARSED is never re-parsed, which is the retry AC expressed as a graph
    # rule rather than just a query filter.
    job = _create_closed_job(authed_client)
    candidate = _add_candidate_with_resume(
        db_session, uuid.UUID(job["job_id"]), "a@example.com", "Moazzam_Resume.pdf"
    )
    candidate.submission_status = "PARSED"
    db_session.commit()

    response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}", json={"submission_status": "SUBMITTED"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"


# --- task execution: TC-04 through TC-09 -------------------------------------
# These call the task function directly (resume_parse_job.run) rather than
# via .delay()/eager mode through the route — that isolates "does the task's
# business logic behave correctly" from "does the HTTP layer wire it up",
# which the enqueue-path tests above already cover.


def _make_task_row(db_session: Session, recruiter: Recruiter, job_id: uuid.UUID) -> BackgroundTask:
    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id, job_id=job_id, task_type=TaskType.RESUME_PARSE
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


# TC-05 — the most important test in the story: one corrupt PDF among five,
# the other four still PARSE, failed=1. Written first, per the story.
def test_one_corrupt_pdf_among_five_does_not_abort_the_batch(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)

    good = [
        _add_candidate_with_resume(db_session, job_id, f"good{i}@example.com", "Moazzam_Resume.pdf")
        for i in range(4)
    ]
    bad = _add_candidate_with_resume(db_session, job_id, "bad@example.com", "corrupt.pdf")

    task = _make_task_row(db_session, recruiter, job_id)
    resume_parse_job.run(str(task.task_id))

    db_session.expire_all()
    for candidate in good:
        db_session.refresh(candidate)
        assert candidate.submission_status == "PARSED"
        assert candidate.resume_text and len(candidate.resume_text.strip()) > 0
        assert candidate.parse_error is None

    db_session.refresh(bad)
    assert bad.submission_status == "PARSE_ERROR"
    assert bad.parse_error
    assert bad.resume_text is None

    db_session.refresh(task)
    assert task.status == TaskStatus.SUCCESS

    counts = task_service.process_status_for_job(db_session, job_id)
    assert counts["total"] == 5
    assert counts["processed"] == 4
    assert counts["failed"] == 1


# TC-04
def test_all_valid_resumes_all_parsed(authed_client: TestClient, db_session: Session) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    for i in range(5):
        _add_candidate_with_resume(db_session, job_id, f"ok{i}@example.com", "Moazzam_Resume.pdf")

    task = _make_task_row(db_session, recruiter, job_id)
    resume_parse_job.run(str(task.task_id))

    counts = task_service.process_status_for_job(db_session, job_id)
    assert counts["processed"] == 5
    assert counts["failed"] == 0


# TC-06
def test_task_raising_outside_loop_marks_task_failed_candidates_untouched(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    candidate = _add_candidate_with_resume(
        db_session, job_id, "a@example.com", "Moazzam_Resume.pdf"
    )

    task = _make_task_row(db_session, recruiter, job_id)
    with (
        patch("app.tasks.resume_parse.get_resume_store", side_effect=RuntimeError("store down")),
        pytest.raises(RuntimeError),
    ):
        resume_parse_job.run(str(task.task_id))

    db_session.expire_all()
    db_session.refresh(task)
    assert task.status == TaskStatus.FAILED
    assert task.error_message
    db_session.refresh(candidate)
    assert candidate.submission_status == "SUBMITTED"  # left retryable, not stuck


# TC-07
def test_running_same_task_twice_does_not_duplicate_work(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    _add_candidate_with_resume(db_session, job_id, "a@example.com", "Moazzam_Resume.pdf")

    task = _make_task_row(db_session, recruiter, job_id)
    resume_parse_job.run(str(task.task_id))
    db_session.expire_all()
    db_session.refresh(task)
    first_completed_at = task.completed_at
    assert task.status == TaskStatus.SUCCESS

    resume_parse_job.run(str(task.task_id))  # same task_id, terminal already
    db_session.expire_all()
    db_session.refresh(task)
    assert task.completed_at == first_completed_at  # untouched — early return

    counts = task_service.process_status_for_job(db_session, job_id)
    assert counts["processed"] == 1
    assert counts["failed"] == 0


# TC-08
def test_scanned_image_pdf_is_parse_error_with_distinct_message(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    scanned = _add_candidate_with_resume(
        db_session, job_id, "scanned@example.com", "scanned_image_resume.pdf"
    )
    corrupt = _add_candidate_with_resume(db_session, job_id, "corrupt@example.com", "corrupt.pdf")

    task = _make_task_row(db_session, recruiter, job_id)
    resume_parse_job.run(str(task.task_id))

    db_session.expire_all()
    db_session.refresh(scanned)
    db_session.refresh(corrupt)
    assert scanned.submission_status == "PARSE_ERROR"
    assert scanned.resume_text is None
    assert corrupt.submission_status == "PARSE_ERROR"
    assert scanned.parse_error != corrupt.parse_error


# TC-09
def test_retrigger_only_reprocesses_parse_error_not_parsed(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)

    good = _add_candidate_with_resume(db_session, job_id, "good@example.com", "Moazzam_Resume.pdf")
    bad = _add_candidate_with_resume(db_session, job_id, "bad@example.com", "corrupt.pdf")

    first_task = _make_task_row(db_session, recruiter, job_id)
    resume_parse_job.run(str(first_task.task_id))
    db_session.expire_all()
    db_session.refresh(good)
    db_session.refresh(bad)
    assert good.submission_status == "PARSED"
    assert bad.submission_status == "PARSE_ERROR"
    original_good_text = good.resume_text

    # Fix the "bad" candidate's stored resume in place, then re-trigger.
    Path(bad.resume_storage_key).write_bytes((_FIXTURES / "Moazzam_Resume.pdf").read_bytes())

    second_task = _make_task_row(db_session, recruiter, job_id)
    resume_parse_job.run(str(second_task.task_id))

    db_session.expire_all()
    db_session.refresh(good)
    db_session.refresh(bad)
    assert good.resume_text == original_good_text  # untouched — PARSED is never re-parsed
    assert bad.submission_status == "PARSED"  # only the PARSE_ERROR one was retried
    assert bad.resume_text is not None
