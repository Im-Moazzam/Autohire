import uuid
from typing import Protocol

from app.models.recruiter import Recruiter


class ResumeStore(Protocol):
    def create_job_folder(self, recruiter: Recruiter, job_id: uuid.UUID, name: str) -> str: ...
