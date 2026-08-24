"""TS-07 Slice 1: RESUME_STORE/MAILER/CALENDAR_STORE/EMBEDDER each pick their
adapter independently of settings.app_env and of each other. No APP_ENV is
set in any of these tests — proving the split actually decoupled them."""

import uuid

import pytest

from app.adapters.calendar_store import (
    GoogleCalendarStore,
    LocalCalendarStore,
    get_calendar_store,
)
from app.adapters.embedder import FastEmbedEmbedder, get_embedder
from app.adapters.mailer import GmailMailer, LocalMailer, get_mailer
from app.adapters.resume_store import DriveResumeStore, LocalResumeStore, get_resume_store
from app.core.config import settings
from app.models.candidate import Candidate
from app.services.candidate_service import resume_url_for


def test_resume_store_defaults_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resume_store", "local")
    assert isinstance(get_resume_store(), LocalResumeStore)


def test_resume_store_switches_to_drive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resume_store", "drive")
    assert isinstance(get_resume_store(), DriveResumeStore)


def test_mailer_defaults_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mailer", "local")
    assert isinstance(get_mailer(), LocalMailer)


def test_mailer_switches_to_gmail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mailer", "gmail")
    assert isinstance(get_mailer(), GmailMailer)


def test_calendar_store_defaults_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "calendar_store", "local")
    assert isinstance(get_calendar_store(), LocalCalendarStore)


def test_calendar_store_switches_to_google(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "calendar_store", "google")
    assert isinstance(get_calendar_store(), GoogleCalendarStore)


def test_embedder_defaults_fastembed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embedder", "fastembed")
    assert isinstance(get_embedder(), FastEmbedEmbedder)


def test_embedder_openai_is_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "embedder", "openai")
    with pytest.raises(NotImplementedError, match="fastembed"):
        get_embedder()


def test_resume_url_for_local_candidate_ignores_app_env() -> None:
    candidate = Candidate(
        candidate_id=uuid.uuid4(),
        resume_storage_key="/storage/resumes/job/file.pdf",
        resume_drive_url=None,
    )
    assert resume_url_for(candidate) == f"/api/v1/candidates/{candidate.candidate_id}/resume"


def test_resume_url_for_drive_candidate_ignores_app_env() -> None:
    candidate = Candidate(
        candidate_id=uuid.uuid4(),
        resume_storage_key=None,
        resume_drive_url="https://drive.google.com/file/abc",
    )
    assert resume_url_for(candidate) == "https://drive.google.com/file/abc"
