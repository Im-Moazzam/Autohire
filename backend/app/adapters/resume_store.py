import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from app.adapters.base import ResumeStore, StoredFile
from app.adapters.google.session import google_call
from app.core.config import settings
from app.models.api_usage_log import ApiName
from app.models.job import JobPosting
from app.models.recruiter import Recruiter

if TYPE_CHECKING:
    from app.models.candidate import Candidate

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def local_job_folder(job_id: uuid.UUID) -> Path:
    # Read settings.local_storage_root at call time, not import time, so
    # tests can point it at a tmp_path without touching the host filesystem.
    return Path(settings.local_storage_root) / "resumes" / str(job_id)


class LocalResumeStore:
    def create_job_folder(self, recruiter: Recruiter, job_id: uuid.UUID, name: str) -> str:
        path = local_job_folder(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def store_resume(
        self,
        recruiter: Recruiter,
        job: JobPosting,
        filename: str,
        content: bytes,
        display_name: str | None = None,
    ) -> StoredFile:
        # display_name is Drive-only (a human-readable label on file
        # metadata); local storage has no such field, the path itself
        # must stay the server-generated name (TC-08).
        folder = local_job_folder(job.job_id)
        folder.mkdir(parents=True, exist_ok=True)
        target = (folder / filename).resolve()
        # Defence in depth: filename is always server-generated (uuid4 + a
        # validated extension), never the candidate's raw name, but this
        # guards the invariant even if that ever changes upstream (TC-08).
        if folder.resolve() not in target.parents:
            raise ValueError(f"resolved resume path {target} escapes job folder {folder}")
        target.write_bytes(content)
        return StoredFile(storage_key=str(target))

    def fetch_resume(self, recruiter: Recruiter, candidate: "Candidate") -> bytes:
        if not candidate.resume_storage_key:
            raise FileNotFoundError(f"no resume stored for candidate {candidate.candidate_id}")
        folder = local_job_folder(candidate.job_id).resolve()
        target = Path(candidate.resume_storage_key).resolve()
        # Same containment guard as store_resume / resolve_resume_path — the
        # stored key is server-generated, but this is defence in depth.
        if folder not in target.parents:
            raise ValueError(f"resolved resume path {target} escapes job folder {folder}")
        return target.read_bytes()


class DriveResumeStore:
    def create_job_folder(self, recruiter: Recruiter, job_id: uuid.UUID, name: str) -> str:
        response = google_call(
            recruiter,
            ApiName.GOOGLE_DRIVE,
            "POST",
            DRIVE_FILES_URL,
            json={"name": name, "mimeType": "application/vnd.google-apps.folder"},
        )
        result: str = response.json()["id"]
        return result

    def store_resume(
        self,
        recruiter: Recruiter,
        job: JobPosting,
        filename: str,
        content: bytes,
        display_name: str | None = None,
    ) -> StoredFile:
        # One multipart/related upload = one google_call = one api_usage_logs
        # row (TC-13) — a create-then-patch-media two-call approach would log
        # twice for a single upload.
        ext = filename.rsplit(".", 1)[-1].lower()
        mime = _MIME_BY_EXT.get(ext, "application/octet-stream")
        boundary = uuid.uuid4().hex
        # Drive's "name" is display metadata only — never used to locate the
        # file (that's drive_file_id) — so it's safe to show the candidate's
        # real filename here even though the on-disk/local name must stay
        # server-generated (TC-08). Falls back to the uuid name if none given.
        drive_name = display_name or filename
        metadata = json.dumps(
            {"name": drive_name, "parents": [job.google_drive_folder_id]}
        ).encode()
        body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n").encode()
        body += metadata
        body += f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n".encode()
        body += content
        body += f"\r\n--{boundary}--".encode()

        response = google_call(
            recruiter,
            ApiName.GOOGLE_DRIVE,
            "POST",
            f"{DRIVE_UPLOAD_URL}?uploadType=multipart&fields=id,webViewLink",
            content=body,
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        )
        data = response.json()
        return StoredFile(
            storage_key=data["id"], drive_file_id=data["id"], drive_url=data.get("webViewLink")
        )

    def fetch_resume(self, recruiter: Recruiter, candidate: "Candidate") -> bytes:
        if not candidate.resume_drive_file_id:
            raise FileNotFoundError(f"no resume stored for candidate {candidate.candidate_id}")
        response = google_call(
            recruiter,
            ApiName.GOOGLE_DRIVE,
            "GET",
            f"{DRIVE_FILES_URL}/{candidate.resume_drive_file_id}?alt=media",
        )
        return response.content


def get_resume_store() -> ResumeStore:
    if settings.resume_store == "local":
        return LocalResumeStore()
    return DriveResumeStore()
