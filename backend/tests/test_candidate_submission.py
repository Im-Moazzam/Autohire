import io
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.resume_store import DriveResumeStore, get_resume_store
from app.core.config import settings
from app.main import app
from app.models.api_usage_log import ApiUsageLog
from app.models.candidate import Candidate, CandidateFormResponse
from app.models.job import JobPosting

_VALID_PDF = b"%PDF-1.4\n%valid pdf content for testing purposes only\n%%EOF"


def _create_template(
    client: TestClient, extra_fields: list[dict] | None = None, name: str = "Standard Software Role"
) -> dict:
    fields = [
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
    ]
    response = client.post(
        "/api/v1/templates",
        json={"template_name": name, "fields": fields + (extra_fields or [])},
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
    email: str = "amina.tariq@example.com",
    full_name: str = "Amina Tariq",
    experience: str = "3",
    filename: str = "resume.pdf",
    content: bytes = _VALID_PDF,
    content_type: str = "application/pdf",
    extra_data: dict[str, str] | None = None,
) -> httpx.Response:
    data = {
        field_ids["Email"]: email,
        field_ids["Full Name"]: full_name,
        field_ids["Years of experience"]: experience,
        **(extra_data or {}),
    }
    files = {"resume": (filename, content, content_type)}
    return TestClient(app).post(f"/api/v1/public/apply/{slug}", data=data, files=files)


def _resumes_dir(job_id: str) -> Path:
    return Path(settings.local_storage_root) / "resumes" / job_id


# TC-01
def test_valid_submission_persists_candidate_and_responses_and_file(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(job["apply_slug"], field_ids)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["message"]
    assert "candidate_id" not in body

    candidates = db_session.query(Candidate).all()
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.email == "amina.tariq@example.com"
    assert candidate.full_name == "Amina Tariq"
    assert candidate.submission_status == "SUBMITTED"
    assert candidate.resume_storage_key is not None

    responses = db_session.query(CandidateFormResponse).filter_by(
        candidate_id=candidate.candidate_id
    )
    assert responses.count() == 3

    stored = Path(candidate.resume_storage_key)
    assert stored.exists()
    assert stored.parent == _resumes_dir(job["job_id"])
    # server-generated: uuid4 + validated extension, never the client's name
    uuid.UUID(stored.stem)
    assert stored.suffix == ".pdf"


# TC-02
def test_missing_required_field_is_422_nothing_written(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(job["apply_slug"], field_ids, full_name="")
    assert response.status_code == 422
    assert db_session.query(Candidate).count() == 0
    assert not _resumes_dir(job["job_id"]).exists() or not any(
        _resumes_dir(job["job_id"]).iterdir()
    )


# TC-03
def test_duplicate_email_same_job_is_409_still_one_row(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    first = _submit(job["apply_slug"], field_ids)
    assert first.status_code == 201

    second = _submit(job["apply_slug"], field_ids)
    assert second.status_code == 409
    assert second.json()["code"] == "DUPLICATE_SUBMISSION"
    assert db_session.query(Candidate).count() == 1


# TC-04
def test_same_email_different_job_is_201_scoped_per_job(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job_a = _create_job(authed_client, template["template_id"], "Role A")
    job_b = _create_job(authed_client, template["template_id"], "Role B")
    field_ids = _field_ids(template)

    first = _submit(job_a["apply_slug"], field_ids)
    second = _submit(job_b["apply_slug"], field_ids)
    assert first.status_code == 201
    assert second.status_code == 201
    assert db_session.query(Candidate).count() == 2


def test_reapplying_after_soft_delete_is_allowed(
    authed_client: TestClient, db_session: Session
) -> None:
    """Partial UNIQUE(job_id, email) WHERE deleted_at IS NULL: a soft-deleted
    candidate must free its email for re-application to the same job."""
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    first = _submit(job["apply_slug"], field_ids)
    assert first.status_code == 201

    row = db_session.query(Candidate).one()
    row.deleted_at = datetime.now(UTC)
    db_session.commit()

    second = _submit(job["apply_slug"], field_ids)
    assert second.status_code == 201, second.text
    assert db_session.query(Candidate).filter_by(deleted_at=None).count() == 1


# TC-05
def test_exe_renamed_to_pdf_is_415_nothing_written(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(
        job["apply_slug"],
        field_ids,
        filename="resume.pdf",
        content=b"MZ\x90\x00\x03\x00\x00\x00fake-exe-content",
        content_type="application/pdf",
    )
    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_FILE_TYPE"
    assert db_session.query(Candidate).count() == 0


# TS-06/R-03: .doc (OLE2) was sniffed and accepted at upload, but
# resume_parser.extract_text has no handler for it — every .doc candidate was
# a silent PARSE_ERROR after the fact. Reject it at upload instead.
def test_ole2_doc_upload_is_415_nothing_written(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(
        job["apply_slug"],
        field_ids,
        filename="resume.doc",
        content=b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"legacy word content",
        content_type="application/msword",
    )
    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_FILE_TYPE"
    assert db_session.query(Candidate).count() == 0


# TC-06
def test_oversized_file_is_413_nothing_written(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    oversized = _VALID_PDF + b"a" * (settings.max_resume_mb * 1024 * 1024 + 1)
    response = _submit(job["apply_slug"], field_ids, content=oversized)
    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"
    assert db_session.query(Candidate).count() == 0


# TC-07
def test_empty_file_is_422(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(job["apply_slug"], field_ids, content=b"")
    assert response.status_code == 422
    assert response.json()["code"] == "EMPTY_FILE"
    assert db_session.query(Candidate).count() == 0


# TC-08
def test_path_traversal_filename_is_stored_under_generated_name(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(job["apply_slug"], field_ids, filename="../../etc/passwd.pdf")
    assert response.status_code == 201, response.text

    candidate = db_session.query(Candidate).one()
    stored = Path(candidate.resume_storage_key)
    assert stored.parent == _resumes_dir(job["job_id"])
    uuid.UUID(stored.stem)
    # nothing escaped the job's resume folder
    storage_root = Path(settings.local_storage_root)
    assert list(storage_root.rglob("passwd.pdf")) == []
    assert list(storage_root.rglob("*.pdf")) == [stored]


# TC-09
def test_field_id_from_another_template_is_422_unknown_field(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    other_template = _create_template(authed_client, name="Other Role")  # unrelated template
    foreign_field_id = _field_ids(other_template)["Years of experience"]

    response = _submit(
        job["apply_slug"], field_ids, extra_data={foreign_field_id: "should not be written"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UNKNOWN_FIELD"
    assert db_session.query(Candidate).count() == 0


def test_non_uuid_field_key_is_422_unknown_field(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(job["apply_slug"], field_ids, extra_data={"not-a-uuid": "value"})
    assert response.status_code == 422
    assert response.json()["code"] == "UNKNOWN_FIELD"
    assert db_session.query(Candidate).count() == 0


# TC-10
def test_storage_failure_is_500_no_candidate_row(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    with patch(
        "app.adapters.resume_store.LocalResumeStore.store_resume",
        side_effect=OSError("disk full"),
    ):
        response = _submit(job["apply_slug"], field_ids)
    assert response.status_code == 500
    assert response.json()["code"] == "RESUME_UPLOAD_FAILED"
    assert db_session.query(Candidate).count() == 0


# TC-11
def test_closed_job_is_410_nothing_written(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    row.status = "CLOSED"
    db_session.commit()

    response = _submit(job["apply_slug"], field_ids)
    assert response.status_code == 410
    assert response.json()["code"] == "JOB_CLOSED"
    assert db_session.query(Candidate).count() == 0


# TC-12
def test_malformed_email_is_422(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(job["apply_slug"], field_ids, email="not-an-email")
    assert response.status_code == 422
    assert db_session.query(Candidate).count() == 0


# TC-13
def test_cloud_mode_uploads_via_google_call_and_logs_once(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    job_row = db_session.get(JobPosting, uuid.UUID(job["job_id"]))
    job_row.google_drive_folder_id = "drive-folder-abc"
    db_session.commit()

    upload_response = httpx.Response(
        200,
        json={
            "id": "drive-file-123",
            "webViewLink": "https://drive.google.com/file/drive-file-123",
        },
        request=httpx.Request("POST", "https://example.com"),
    )

    # candidate_service reads settings.app_env directly (same local/cloud
    # branch job_service.finalize_launch uses) to decide which column to
    # populate — overriding just the store dependency isn't enough.
    original_env = settings.app_env
    settings.app_env = "cloud"
    app.dependency_overrides[get_resume_store] = lambda: DriveResumeStore()
    try:
        with patch(
            "app.adapters.google.session.httpx.request", return_value=upload_response
        ) as mock_request:
            response = _submit(job["apply_slug"], field_ids)
    finally:
        app.dependency_overrides.pop(get_resume_store, None)
        settings.app_env = original_env

    assert response.status_code == 201, response.text
    assert mock_request.call_count == 1

    candidate = db_session.query(Candidate).one()
    assert candidate.resume_drive_file_id == "drive-file-123"
    assert candidate.resume_drive_url == "https://drive.google.com/file/drive-file-123"
    assert candidate.resume_storage_key is None

    rows = db_session.query(ApiUsageLog).filter_by(recruiter_id=job_row.recruiter_id).all()
    assert len(rows) == 1
    assert rows[0].api_name == "GOOGLE_DRIVE"


def test_response_value_over_length_cap_is_422(
    authed_client: TestClient, db_session: Session
) -> None:
    template = _create_template(
        authed_client,
        extra_fields=[
            {
                "field_label": "Cover letter",
                "field_type": "PARAGRAPH",
                "is_required": False,
                "field_order": 3,
            }
        ],
    )
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(
        job["apply_slug"],
        field_ids,
        extra_data={field_ids["Cover letter"]: "x" * 5001},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert db_session.query(Candidate).count() == 0


def _valid_docx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<doc/>")
    return buf.getvalue()


def test_valid_docx_accepted(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    response = _submit(
        job["apply_slug"],
        field_ids,
        filename="resume.docx",
        content=_valid_docx_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 201, response.text
    candidate = db_session.query(Candidate).one()
    assert Path(candidate.resume_storage_key).suffix == ".docx"


def test_plain_zip_is_not_accepted_as_docx(authed_client: TestClient, db_session: Session) -> None:
    template = _create_template(authed_client)
    job = _create_job(authed_client, template["template_id"])
    field_ids = _field_ids(template)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("hello.txt", "hi")

    response = _submit(
        job["apply_slug"],
        field_ids,
        filename="resume.docx",
        content=buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 415
    assert db_session.query(Candidate).count() == 0
