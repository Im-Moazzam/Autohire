import uuid
from pathlib import Path

from app.adapters.base import ResumeStore, StoredFile
from app.adapters.google.session import google_call
from app.core.config import settings
from app.models.api_usage_log import ApiName
from app.models.job import JobPosting
from app.models.recruiter import Recruiter

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

_MIME_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
}


class LocalResumeStore:
    def create_job_folder(self, recruiter: Recruiter, job_id: uuid.UUID, name: str) -> str:
        # Read settings.local_storage_root at call time, not import time, so
        # tests can point it at a tmp_path without touching the host filesystem.
        path = Path(settings.local_storage_root) / "resumes" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def store_resume(
        self, recruiter: Recruiter, job: JobPosting, filename: str, content: bytes
    ) -> StoredFile:
        folder = Path(settings.local_storage_root) / "resumes" / str(job.job_id)
        folder.mkdir(parents=True, exist_ok=True)
        target = (folder / filename).resolve()
        # Defence in depth: filename is always server-generated (uuid4 + a
        # validated extension), never the candidate's raw name, but this
        # guards the invariant even if that ever changes upstream (TC-08).
        if folder.resolve() not in target.parents:
            raise ValueError(f"resolved resume path {target} escapes job folder {folder}")
        target.write_bytes(content)
        return StoredFile(storage_key=str(target))


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
        self, recruiter: Recruiter, job: JobPosting, filename: str, content: bytes
    ) -> StoredFile:
        # One multipart/related upload = one google_call = one api_usage_logs
        # row (TC-13) — a create-then-patch-media two-call approach would log
        # twice for a single upload.
        ext = filename.rsplit(".", 1)[-1].lower()
        mime = _MIME_BY_EXT.get(ext, "application/octet-stream")
        boundary = uuid.uuid4().hex
        metadata = (
            f'{{"name": "{filename}", "parents": ["{job.google_drive_folder_id}"]}}'
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


def get_resume_store() -> ResumeStore:
    if settings.app_env == "local":
        return LocalResumeStore()
    return DriveResumeStore()
