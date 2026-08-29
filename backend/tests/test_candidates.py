import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import app
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.candidate import Candidate, CandidateFormResponse
from app.models.recruiter import Recruiter
from app.services.auth_service import SESSION_COOKIE, create_session_cookie
from tests.conftest import QueryCounter

_VALID_PDF = b"%PDF-1.4\n%valid pdf content for testing purposes only\n%%EOF"


def _create_template(client: TestClient, name: str = "Standard Software Role") -> dict:
    response = client.post(
        "/api/v1/templates",
        json={
            "template_name": name,
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
                {
                    "field_label": "Years of experience",
                    "field_type": "NUMBER",
                    "is_required": True,
                    "field_order": 2,
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_job(
    client: TestClient, template_id: str, title: str = "Senior Backend Engineer"
) -> dict:
    response = client.post(
        "/api/v1/jobs",
        json={
            "job_title": title,
            "job_description": "Own the API layer.",
            "template_id": template_id,
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _field_ids(template: dict) -> dict[str, str]:
    return {f["field_label"]: f["field_id"] for f in template["fields"]}


def _submit(
    slug: str,
    field_ids: dict[str, str],
    email: str,
    full_name: str,
    experience: str = "3",
) -> httpx.Response:
    data = {
        field_ids["Email"]: email,
        field_ids["Full Name"]: full_name,
        field_ids["Years of experience"]: experience,
    }
    files = {"resume": ("resume.pdf", _VALID_PDF, "application/pdf")}
    return TestClient(app).post(f"/api/v1/public/apply/{slug}", data=data, files=files)


def _other_client(recruiter: Recruiter) -> TestClient:
    other = TestClient(app)
    other.cookies.set(SESSION_COOKIE, create_session_cookie(str(recruiter.recruiter_id)))
    return other


def _add_candidate(
    db_session: Session,
    job_id: uuid.UUID,
    email: str,
    full_name: str = "Test Candidate",
    submission_status: str = "SUBMITTED",
    submitted_at: datetime | None = None,
    parse_error: str | None = None,
    deleted: bool = False,
    resume_storage_key: str | None = None,
    resume_text: str | None = None,
) -> Candidate:
    candidate = Candidate(
        job_id=job_id,
        full_name=full_name,
        email=email,
        submission_status=submission_status,
        submitted_at=submitted_at or datetime.now(UTC),
        parse_error=parse_error,
        deleted_at=datetime.now(UTC) if deleted else None,
        resume_storage_key=resume_storage_key,
        resume_text=resume_text,
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


# TC-01
def test_list_returns_all_newest_first(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    job_id = uuid.UUID(job["job_id"])
    now = datetime.now(UTC)
    _add_candidate(db_session, job_id, "a@example.com", submitted_at=now - timedelta(hours=3))
    _add_candidate(db_session, job_id, "b@example.com", submitted_at=now - timedelta(hours=1))
    _add_candidate(db_session, job_id, "c@example.com", submitted_at=now - timedelta(hours=2))

    response = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    emails = [item["email"] for item in body["items"]]
    assert emails == ["b@example.com", "c@example.com", "a@example.com"]


# TC-02
def test_list_another_recruiters_job_is_404(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    _add_candidate(db_session, uuid.UUID(job["job_id"]), "a@example.com")

    other = _other_client(second_recruiter)
    response = other.get(f"/api/v1/jobs/{job['job_id']}/candidates")
    assert response.status_code == 404
    assert response.json()["code"] == "JOB_NOT_FOUND"


# TC-03
def test_list_filters_by_submission_status(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    job_id = uuid.UUID(job["job_id"])
    _add_candidate(db_session, job_id, "ok@example.com", submission_status="SUBMITTED")
    _add_candidate(
        db_session,
        job_id,
        "bad@example.com",
        submission_status="PARSE_ERROR",
        parse_error="OCR failed.",
    )

    response = authed_client.get(
        f"/api/v1/jobs/{job['job_id']}/candidates", params={"submission_status": "PARSE_ERROR"}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["email"] == "bad@example.com"
    assert body["items"][0]["parse_error"] == "OCR failed."


# TC-04
def test_soft_deleted_candidate_excluded_from_list_and_detail(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session, uuid.UUID(job["job_id"]), "gone@example.com", deleted=True
    )

    list_response = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates")
    assert list_response.json()["total"] == 0

    detail_response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert detail_response.status_code == 404
    assert detail_response.json()["code"] == "CANDIDATE_NOT_FOUND"


# TC-05
def test_detail_form_responses_carry_correct_field_label(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    candidate = _add_candidate(db_session, uuid.UUID(job["job_id"]), "labeled@example.com")
    db_session.add_all(
        [
            CandidateFormResponse(
                candidate_id=candidate.candidate_id,
                field_id=uuid.UUID(field_ids["Email"]),
                response_value="labeled@example.com",
            ),
            CandidateFormResponse(
                candidate_id=candidate.candidate_id,
                field_id=uuid.UUID(field_ids["Years of experience"]),
                response_value="7",
            ),
        ]
    )
    db_session.commit()

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert response.status_code == 200
    by_label = {fr["field_label"]: fr["response_value"] for fr in response.json()["form_responses"]}
    assert by_label["Email"] == "labeled@example.com"
    assert by_label["Years of experience"] == "7"


# TC-06
def test_detail_another_recruiters_candidate_is_404(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(db_session, uuid.UUID(job["job_id"]), "mine@example.com")

    other = _other_client(second_recruiter)
    response = other.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "CANDIDATE_NOT_FOUND"


# TC-07
def test_list_pagination_correct_total_and_page(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    job_id = uuid.UUID(job["job_id"])
    now = datetime.now(UTC)
    for i in range(5):
        _add_candidate(
            db_session, job_id, f"c{i}@example.com", submitted_at=now - timedelta(hours=i)
        )

    response = authed_client.get(
        f"/api/v1/jobs/{job['job_id']}/candidates", params={"page": 2, "size": 2}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
    assert len(body["items"]) == 2
    # page 1 holds c0,c1 (newest first); page 2 holds c2,c3
    assert [item["email"] for item in body["items"]] == ["c2@example.com", "c3@example.com"]


def _submit_with_resume(authed_client: TestClient) -> tuple[dict, dict]:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)
    submit = _submit(job["apply_slug"], field_ids, "resume-holder@example.com", "Resume Holder")
    assert submit.status_code == 201, submit.text
    return job, field_ids


# TC-08
def test_download_another_recruiters_resume_is_404_no_stream(
    authed_client: TestClient, second_recruiter: Recruiter, db_session: Session
) -> None:
    _submit_with_resume(authed_client)
    candidate = db_session.query(Candidate).one()

    other = _other_client(second_recruiter)
    response = other.get(f"/api/v1/candidates/{candidate.candidate_id}/resume")
    assert response.status_code == 404
    assert response.json()["code"] == "CANDIDATE_NOT_FOUND"
    # the file was never streamed — the body is the error envelope, not the PDF
    assert response.content != _VALID_PDF
    assert response.headers["content-type"].startswith("application/json")


# TC-09
def test_download_no_stored_resume_is_404(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session, uuid.UUID(job["job_id"]), "no-resume@example.com", resume_storage_key=None
    )

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}/resume")
    assert response.status_code == 404
    assert response.json()["code"] == "RESUME_NOT_FOUND"


def test_download_happy_path_streams_bytes_as_attachment(
    authed_client: TestClient, db_session: Session
) -> None:
    _submit_with_resume(authed_client)
    candidate = db_session.query(Candidate).one()

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}/resume")
    assert response.status_code == 200
    assert response.content == _VALID_PDF
    assert response.headers["content-type"] == "application/pdf"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment")
    stored_name = Path(candidate.resume_storage_key).name
    assert stored_name in disposition
    uuid.UUID(Path(candidate.resume_storage_key).stem)  # server-generated, not candidate-supplied


def test_download_path_outside_job_folder_is_404(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    escaping = Path(settings.local_storage_root) / "escaped.pdf"
    escaping.write_bytes(_VALID_PDF)
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "escapee@example.com",
        resume_storage_key=str(escaping),
    )

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}/resume")
    assert response.status_code == 404
    assert response.json()["code"] == "RESUME_NOT_FOUND"


def test_resume_url_is_local_route_never_a_filesystem_path(
    authed_client: TestClient, db_session: Session
) -> None:
    job, _ = _submit_with_resume(authed_client)
    candidate = db_session.query(Candidate).one()

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert response.status_code == 200
    resume_url = response.json()["resume_url"]
    assert resume_url == f"/api/v1/candidates/{candidate.candidate_id}/resume"
    assert settings.local_storage_root not in resume_url
    assert str(candidate.candidate_id) in resume_url


# TC-10
def test_list_query_count_is_bounded_regardless_of_page_size(
    authed_client: TestClient, db_session: Session, query_counter: QueryCounter
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    job_id = uuid.UUID(job["job_id"])
    for i in range(6):
        _add_candidate(db_session, job_id, f"q{i}@example.com")

    # expire_all forces both requests to start from a cold identity map, so
    # a difference in count can only come from route logic, never from one
    # request incidentally reusing an already-loaded Recruiter/JobPosting row.
    db_session.expire_all()
    query_counter.count = 0
    small = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates", params={"size": 2})
    assert small.status_code == 200
    small_count = query_counter.count

    db_session.expire_all()
    query_counter.count = 0
    large = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates", params={"size": 50})
    assert large.status_code == 200
    large_count = query_counter.count

    assert small_count == large_count
    assert small_count <= 5


def test_patch_status_change_only(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(db_session, uuid.UUID(job["job_id"]), "patchable@example.com")

    response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}", json={"submission_status": "REJECTED"}
    )
    assert response.status_code == 200
    assert response.json()["submission_status"] == "REJECTED"


def test_restorable_status_submitted_when_never_processed(
    authed_client: TestClient, db_session: Session
) -> None:
    """A job still LIVE (never closed/processed) can only ever produce
    SUBMITTED candidates — undoing a rejection must land back on SUBMITTED,
    not silently upgrade to PARSED just because that used to be the only
    legal target."""
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "never-processed@example.com",
        submission_status="REJECTED",
    )

    get_response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert get_response.json()["restorable_status"] == "SUBMITTED"

    patch_response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}", json={"submission_status": "SUBMITTED"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["submission_status"] == "SUBMITTED"


def test_restorable_status_parsed_when_resume_parsed_but_not_ranked(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "parsed-not-ranked@example.com",
        submission_status="REJECTED",
        resume_text="Experienced backend engineer...",
    )

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert response.json()["restorable_status"] == "PARSED"


def test_restorable_status_ranked_when_analysis_row_exists(
    authed_client: TestClient, db_session: Session
) -> None:
    """A candidate rejected after being ranked keeps their real
    ai_analysis_results row — undoing must restore RANKED, not PARSED,
    so "Schedule interview" reappears instead of a re-rank being required."""
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "ranked-then-rejected@example.com",
        submission_status="REJECTED",
        resume_text="Experienced backend engineer...",
    )
    db_session.add(
        AiAnalysisResult(
            candidate_id=candidate.candidate_id,
            job_id=uuid.UUID(job["job_id"]),
            semantic_score=0.82,
            rank_position=1,
        )
    )
    db_session.commit()

    get_response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert get_response.json()["restorable_status"] == "RANKED"

    patch_response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}", json={"submission_status": "RANKED"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["submission_status"] == "RANKED"


def test_restorable_status_parse_error_when_parse_failed(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "parse-failed@example.com",
        submission_status="REJECTED",
        parse_error="Scanned image, no extractable text.",
    )

    response = authed_client.get(f"/api/v1/candidates/{candidate.candidate_id}")
    assert response.json()["restorable_status"] == "PARSE_ERROR"


def test_list_candidates_includes_restorable_status(
    authed_client: TestClient, db_session: Session
) -> None:
    """The list endpoint computes restorable_status via a single batched
    query (ranking_exists_map), never N+1 over the page."""
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    _add_candidate(
        db_session, uuid.UUID(job["job_id"]), "listed@example.com", submission_status="REJECTED"
    )

    response = authed_client.get(f"/api/v1/jobs/{job['job_id']}/candidates")
    assert response.status_code == 200
    assert response.json()["items"][0]["restorable_status"] == "SUBMITTED"


def test_patch_reject_then_invite_is_invalid_without_undo_first(
    authed_client: TestClient, db_session: Session
) -> None:
    """One obvious way back in: a rejected candidate must be undone (to
    whatever compute_restorable_status derives) before they can be invited —
    no direct REJECTED -> INVITED shortcut."""
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "second-chance@example.com",
        submission_status="REJECTED",
    )

    response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}", json={"submission_status": "INVITED"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"


def test_patch_declined_stays_terminal(authed_client: TestClient, db_session: Session) -> None:
    """Unlike REJECTED, DECLINED is the candidate's own answer, not the
    recruiter's — it must stay terminal even after the REJECTED back-edge."""
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(
        db_session,
        uuid.UUID(job["job_id"]),
        "declined@example.com",
        submission_status="DECLINED",
    )

    response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}", json={"submission_status": "RANKED"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"


def test_patch_rejects_unknown_field(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    candidate = _add_candidate(db_session, uuid.UUID(job["job_id"]), "immutable@example.com")

    response = authed_client.patch(
        f"/api/v1/candidates/{candidate.candidate_id}",
        json={"submission_status": "REJECTED", "email": "hijacked@example.com"},
    )
    assert response.status_code == 422
