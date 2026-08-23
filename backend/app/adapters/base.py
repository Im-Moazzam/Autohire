import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from app.models.recruiter import Recruiter

if TYPE_CHECKING:
    from app.models.candidate import Candidate
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

    def fetch_resume(self, recruiter: Recruiter, candidate: "Candidate") -> bytes: ...


@dataclass(frozen=True)
class ResumeAnalysis:
    """What the LLM adapter produces. Deliberately has no score field — the
    score is cosine similarity, computed by VectorStore, and nothing here can
    become semantic_score (US-18's headline rule)."""

    matched_skills: list[str]
    missing_skills: list[str]
    feedback: str | None
    evidence_snippets: list[str] | None


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    def cosine_similarity(self, vector_a: list[float], vector_b: list[float]) -> float: ...


class ResumeAnalyzer(Protocol):
    def analyze(self, jd_text: str, resume_text: str) -> ResumeAnalysis: ...


@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    meet_link: str | None = None


class CalendarStore(Protocol):
    def create_event(
        self,
        recruiter: Recruiter,
        *,
        summary: str,
        description: str,
        starts_at: datetime,
        duration_minutes: int,
        attendee_email: str,
    ) -> CalendarEvent: ...


@dataclass(frozen=True)
class SentMessage:
    message_id: str | None = None
    thread_id: str | None = None


class Mailer(Protocol):
    def send(self, recruiter: Recruiter, *, to: str, subject: str, body: str) -> SentMessage: ...
