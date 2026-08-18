import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from app.models.recruiter import Recruiter

if TYPE_CHECKING:
    from app.models.job import JobPosting


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    drive_file_id: str | None = None
    drive_url: str | None = None


class ResumeStore(Protocol):
    def create_job_folder(self, recruiter: Recruiter, job_id: uuid.UUID, name: str) -> str: ...

    def store_resume(
        self, recruiter: Recruiter, job: "JobPosting", filename: str, content: bytes
    ) -> StoredFile: ...
