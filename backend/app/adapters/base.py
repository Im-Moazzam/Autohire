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
        self,
        recruiter: Recruiter,
        job: "JobPosting",
        filename: str,
        content: bytes,
        display_name: str | None = None,
    ) -> StoredFile: ...

    def fetch_resume(self, recruiter: Recruiter, candidate: "Candidate") -> bytes: ...


@dataclass(frozen=True)
class ResumeAnalysis:
    """What the analyzer adapter produces.

    US-18 deliberately gave this no score field, so that an LLM number could
    never become semantic_score. ADR-006 reverses that: ranking is now hybrid,
    and relevance_score is the model's half of it.

    relevance_score is 0-100 (not 0-1) because a bounded integer is markedly
    more stable across runs than a free float, and it is *not* semantic_score —
    semantic_score stays pure cosine similarity, computed by VectorStore. The
    blend lives in batch_ranking; an adapter never decides the weight.
    None means the analyzer had no opinion, and final_score falls back to
    cosine alone rather than penalising the candidate.
    """

    matched_skills: list[str]
    missing_skills: list[str]
    feedback: str | None
    evidence_snippets: list[str] | None
    relevance_score: int | None = None


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

    def delete_event(self, recruiter: Recruiter, event_id: str) -> None: ...


@dataclass(frozen=True)
class SentMessage:
    message_id: str | None = None
    thread_id: str | None = None


class Mailer(Protocol):
    def send(self, recruiter: Recruiter, *, to: str, subject: str, body: str) -> SentMessage: ...
