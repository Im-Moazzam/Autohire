import uuid
from pathlib import Path

from app.adapters.base import ResumeStore
from app.adapters.google.session import google_call
from app.core.config import settings
from app.models.api_usage_log import ApiName
from app.models.recruiter import Recruiter

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


class LocalResumeStore:
    def create_job_folder(self, recruiter: Recruiter, job_id: uuid.UUID, name: str) -> str:
        # Read settings.local_storage_root at call time, not import time, so
        # tests can point it at a tmp_path without touching the host filesystem.
        path = Path(settings.local_storage_root) / "resumes" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)


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


def get_resume_store() -> ResumeStore:
    if settings.app_env == "local":
        return LocalResumeStore()
    return DriveResumeStore()
