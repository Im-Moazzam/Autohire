import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.background_task import BackgroundTask
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.enums import TaskStatus, TaskType
from app.services import task_service
from app.services.auth_service import SESSION_COOKIE, create_session_cookie
from app.tasks.batch_ranking import batch_ranking_job
from tests.conftest import QueryCounter

# --- deterministic fake embedder — no model download, exact TC-04/TC-07 -----


def _fake_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [(digest[i % len(digest)] - 128) / 128 for i in range(settings.embedding_dim)]


class _FakeEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_fake_vector(t) for t in texts]


def _patch_embedder():
    return patch("app.tasks.batch_ranking.get_embedder", return_value=_FakeEmbedder())


# --- fixtures / helpers -------------------------------------------------------


def _create_template(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/templates",
        json={
            "template_name": f"Ranking Story Role {uuid.uuid4()}",
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


def _create_closed_job(
    client: TestClient, description: str = "Backend role needing python and sql."
) -> dict:
    template = _create_template(client)
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": "Backend Engineer",
            "job_description": description,
            "template_id": template["template_id"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    job = response.json()
    close = client.patch(f"/api/v1/jobs/{job['job_id']}", json={"status": "CLOSED"})
    assert close.status_code == 200, close.text
    return close.json()


def _add_candidate(
    db_session: Session,
    job_id: uuid.UUID,
    email: str,
    resume_text: str,
    status: str = "PARSED",
    submitted_at: datetime | None = None,
) -> Candidate:
    candidate = Candidate(
        job_id=job_id,
        full_name=email.split("@")[0],
        email=email,
        submission_status=status,
        resume_text=resume_text,
        submitted_at=submitted_at or datetime.now(UTC),
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def _get_recruiter(db_session: Session) -> Recruiter:
    return db_session.query(Recruiter).one()


def _make_task_row(db_session: Session, recruiter: Recruiter, job_id: uuid.UUID) -> BackgroundTask:
    task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id, job_id=job_id, task_type=TaskType.BATCH_RANKING
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def _mock_rank_delay():
    return patch(
        "app.services.task_service.batch_ranking_job.delay", return_value=Mock(id="fake-celery-id")
    )


# TS-06/R-11: an exception inside _run_batch_ranking (not a per-candidate
# analyzer failure, which degrades to NULL skills and continues) must mark
# the task FAILED and re-raise, mirroring resume_parse_job's equivalent path.
def test_batch_ranking_exception_outside_loop_marks_task_failed(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    _add_candidate(db_session, job_id, "a@example.com", "python developer")

    task = _make_task_row(db_session, recruiter, job_id)
    with (
        patch("app.tasks.batch_ranking.get_embedder", side_effect=RuntimeError("model down")),
        pytest.raises(RuntimeError),
    ):
        batch_ranking_job.run(str(task.task_id))

    db_session.expire_all()
    db_session.refresh(task)
    assert task.status == TaskStatus.FAILED
    assert task.error_message
    assert task.completed_at is not None


# --- TC-01 --------------------------------------------------------------------


def test_five_parsed_candidates_all_ranked(authed_client: TestClient, db_session: Session) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    for i in range(5):
        _add_candidate(db_session, job_id, f"c{i}@example.com", f"python developer number {i}")

    task = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task.task_id))

    rows = db_session.query(AiAnalysisResult).filter_by(job_id=job_id).all()
    assert len(rows) == 5
    assert sorted(r.rank_position for r in rows) == [1, 2, 3, 4, 5]
    for c in db_session.query(Candidate).filter_by(job_id=job_id).all():
        assert c.submission_status == "RANKED"


# --- TC-02 ----------------------------------------------------------------


def test_parse_error_candidate_is_skipped_not_scored_zero(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    good = _add_candidate(db_session, job_id, "good@example.com", "python developer")
    failed = _add_candidate(db_session, job_id, "bad@example.com", "", status="PARSE_ERROR")

    task = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task.task_id))

    assert db_session.query(AiAnalysisResult).filter_by(candidate_id=good.candidate_id).count() == 1
    assert (
        db_session.query(AiAnalysisResult).filter_by(candidate_id=failed.candidate_id).count() == 0
    )
    db_session.refresh(failed)
    assert failed.submission_status == "PARSE_ERROR"


# --- TC-03 ----------------------------------------------------------------


def test_reranking_replaces_rows_not_duplicates(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    _add_candidate(db_session, job_id, "a@example.com", "python developer")
    _add_candidate(db_session, job_id, "b@example.com", "sql specialist")

    task1 = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task1.task_id))
    assert db_session.query(AiAnalysisResult).filter_by(job_id=job_id).count() == 2

    # After run 1 nothing is PARSED anymore — a PARSED-only filter would make
    # this a no-op. RANKED candidates must still be selected for re-ranking.
    task2 = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task2.task_id))

    rows = db_session.query(AiAnalysisResult).filter_by(job_id=job_id).all()
    assert len(rows) == 2  # still one per candidate, not four


# --- TC-04 ------------------------------------------------------------------


def test_identical_resumes_rank_deterministically_across_runs(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    now = datetime.now(UTC)
    a = _add_candidate(db_session, job_id, "a@example.com", "same resume text", submitted_at=now)
    b = _add_candidate(
        db_session,
        job_id,
        "b@example.com",
        "same resume text",
        submitted_at=now + timedelta(seconds=1),
    )

    task1 = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task1.task_id))
    db_session.expire_all()
    first_order = {
        r.candidate_id: r.rank_position
        for r in db_session.query(AiAnalysisResult).filter_by(job_id=job_id).all()
    }
    first_scores = {
        r.candidate_id: r.semantic_score for r in db_session.query(AiAnalysisResult).all()
    }

    task2 = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task2.task_id))
    db_session.expire_all()
    second_order = {
        r.candidate_id: r.rank_position
        for r in db_session.query(AiAnalysisResult).filter_by(job_id=job_id).all()
    }
    second_scores = {
        r.candidate_id: r.semantic_score for r in db_session.query(AiAnalysisResult).all()
    }

    assert first_order == second_order
    assert first_order[a.candidate_id] == 1  # earlier submitted_at wins the tie
    assert first_order[b.candidate_id] == 2
    # Reproducibility of the number itself, not just the ordering — the thing
    # that has to be defensible as "the score is cosine similarity, full stop".
    assert first_scores == second_scores


# --- TC-05 --------------------------------------------------------------------


def test_analyzer_failure_leaves_score_and_rank_intact(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    candidate = _add_candidate(db_session, job_id, "a@example.com", "python developer")

    task = _make_task_row(db_session, recruiter, job_id)
    with (
        _patch_embedder(),
        patch(
            "app.tasks.batch_ranking.get_analyzer",
            return_value=Mock(analyze=Mock(side_effect=RuntimeError("llm down"))),
        ),
    ):
        batch_ranking_job.run(str(task.task_id))

    row = db_session.query(AiAnalysisResult).filter_by(candidate_id=candidate.candidate_id).one()
    assert row.rank_position == 1
    assert row.semantic_score is not None
    assert row.matched_skills is None
    assert row.ai_feedback_summary is None
    db_session.refresh(candidate)
    assert candidate.submission_status == "RANKED"


# --- TC-06 ----------------------------------------------------------------


def test_trigger_rank_with_no_parsed_candidates_is_409(authed_client: TestClient) -> None:
    job = _create_closed_job(authed_client)
    with _mock_rank_delay():
        response = authed_client.post(f"/api/v1/jobs/{job['job_id']}/rank")
    assert response.status_code == 409
    assert response.json()["code"] == "NO_PARSED_CANDIDATES"


# --- TC-07 ------------------------------------------------------------------


def test_embedding_column_dimension_matches_settings(db_session: Session) -> None:
    dim = db_session.execute(
        text(
            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
            "WHERE attrelid = 'ai_analysis_results'::regclass AND attname = 'embedding'"
        )
    ).scalar()
    assert dim == f"vector({settings.embedding_dim})"


# --- TC-08 ------------------------------------------------------------------


def test_rank_while_resume_parse_pending_is_409(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    _add_candidate(db_session, job_id, "a@example.com", "python developer", status="SUBMITTED")

    parse_task = BackgroundTask(
        recruiter_id=recruiter.recruiter_id, job_id=job_id, task_type=TaskType.RESUME_PARSE
    )
    db_session.add(parse_task)
    db_session.commit()

    with _mock_rank_delay():
        response = authed_client.post(f"/api/v1/jobs/{job['job_id']}/rank")
    assert response.status_code == 409
    assert response.json()["code"] == "PROCESSING_IN_PROGRESS"


def test_widened_index_backstops_concurrent_rank_and_parse(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    _add_candidate(db_session, job_id, "a@example.com", "python developer")

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
    with (
        patch("app.services.task_service.active_task_for_job", return_value=None),
        pytest.raises(HTTPException) as exc_info,
    ):
        task_service.enqueue_batch_ranking(db_session, recruiter, job_row)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "PROCESSING_IN_PROGRESS"
    rows = db_session.query(BackgroundTask).filter_by(job_id=job_id).all()
    assert len(rows) == 1


# --- TC-09 ----------------------------------------------------------------


def test_ranked_endpoint_returns_ranked_and_failed_separately(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    for i in range(4):
        _add_candidate(db_session, job_id, f"good{i}@example.com", f"python dev {i}")
    _add_candidate(
        db_session,
        job_id,
        "bad@example.com",
        "",
        status="PARSE_ERROR",
    )
    db_session.query(Candidate).filter_by(email="bad@example.com").update(
        {"parse_error": "no text layer"}
    )
    db_session.commit()

    task = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task.task_id))

    ranked = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates/ranked")
    assert ranked.status_code == 200
    assert len(ranked.json()["items"]) == 4

    failed = authed_client.get(
        f"/api/v1/jobs/{job['job_id']}/candidates", params={"submission_status": "PARSE_ERROR"}
    )
    assert failed.status_code == 200
    assert len(failed.json()["items"]) == 1
    assert failed.json()["items"][0]["parse_error"] == "no text layer"


# --- TC-10 ----------------------------------------------------------------


def test_never_ranked_job_is_empty_not_404(authed_client: TestClient) -> None:
    job = _create_closed_job(authed_client)
    response = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates/ranked")
    assert response.status_code == 200
    assert response.json()["items"] == []

    detail = authed_client.get(f"/api/v1/jobs/{job['job_id']}")
    assert detail.status_code == 200
    assert detail.json()["processed_at"] is None


# --- TC-11 ------------------------------------------------------------------


def test_only_failures_ranked_empty_failed_populated(
    authed_client: TestClient, db_session: Session
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    _add_candidate(db_session, job_id, "bad@example.com", "", status="PARSE_ERROR")

    ranked = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates/ranked")
    assert ranked.json()["items"] == []
    failed = authed_client.get(
        f"/api/v1/jobs/{job['job_id']}/candidates", params={"submission_status": "PARSE_ERROR"}
    )
    assert len(failed.json()["items"]) == 1


# --- TC-12 ------------------------------------------------------------------


def test_ranked_endpoint_is_404_cross_tenant(
    authed_client: TestClient, second_recruiter: Recruiter
) -> None:
    job = _create_closed_job(authed_client)
    other = TestClient(authed_client.app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(second_recruiter.recruiter_id)))

    ranked = other.get(f"/api/v1/jobs/{job['job_id']}/candidates/ranked")
    assert ranked.status_code == 404

    with _mock_rank_delay():
        rank = other.post(f"/api/v1/jobs/{job['job_id']}/rank")
    assert rank.status_code == 404


# --- TC-13 ------------------------------------------------------------------


def test_ranked_endpoint_query_count_is_bounded(
    authed_client: TestClient, db_session: Session, query_counter: QueryCounter
) -> None:
    job = _create_closed_job(authed_client)
    job_id = uuid.UUID(job["job_id"])
    recruiter = _get_recruiter(db_session)
    for i in range(3):
        _add_candidate(db_session, job_id, f"c{i}@example.com", f"python dev {i}")
    task = _make_task_row(db_session, recruiter, job_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task.task_id))

    query_counter.count = 0
    authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates/ranked")
    small_count = query_counter.count

    job2 = _create_closed_job(authed_client)
    job2_id = uuid.UUID(job2["job_id"])
    for i in range(30):
        _add_candidate(db_session, job2_id, f"d{i}@example.com", f"python dev {i}")
    task2 = _make_task_row(db_session, recruiter, job2_id)
    with _patch_embedder():
        batch_ranking_job.run(str(task2.task_id))

    query_counter.count = 0
    authed_client.get(f"/api/v1/jobs/{job2['job_id']}/candidates/ranked")
    large_count = query_counter.count

    assert small_count == large_count
