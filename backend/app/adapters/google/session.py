"""The wrapper every Google API call goes through.

Decrypt -> refresh if stale -> call with retry -> log usage. See
docs/architecture.md §Google token handling.

google_call is sync (httpx.request, time.sleep) by design — it must never be
awaited from an `async def` route, or the retry backoff blocks the event loop.
"""

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.core.crypto import decrypt_token, encrypt_token
from app.core.db import SessionLocal
from app.core.exceptions import ReauthRequired
from app.models.api_usage_log import ApiName, ApiUsageLog
from app.models.recruiter import Recruiter, RecruiterState

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

MAX_ATTEMPTS = 3
REFRESH_SKEW = timedelta(seconds=60)
_BACKOFF_BASE_SECONDS = 1.0


def _is_backoff_retryable(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def google_call(
    recruiter: Recruiter, api_name: ApiName, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    _ensure_authorized(recruiter)

    access_token = _current_access_token(recruiter)

    caller_headers = kwargs.pop("headers", {})

    attempts = 0
    response: httpx.Response | None = None
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            attempts = attempt
            headers = {"Authorization": f"Bearer {access_token}", **caller_headers}
            response = httpx.request(method, url, headers=headers, **kwargs)
            if response.status_code < 400:
                return response

            status = response.status_code
            retryable = status == 401 or _is_backoff_retryable(status)
            if not retryable or attempt == MAX_ATTEMPTS:
                break

            if response.status_code == 401:
                access_token = _refresh_and_persist(recruiter)
            else:
                time.sleep(_BACKOFF_BASE_SECONDS * 2 ** (attempt - 1))

        assert response is not None  # loop always runs at least once
        response.raise_for_status()
        return response
    finally:
        if attempts:
            _log_usage(recruiter.recruiter_id, api_name, attempts)


def _ensure_authorized(recruiter: Recruiter) -> None:
    already_reauth = recruiter.account_state == RecruiterState.REAUTH_REQUIRED
    if already_reauth or not recruiter.google_refresh_token:
        raise ReauthRequired()


def _current_access_token(recruiter: Recruiter) -> str:
    if recruiter.google_token_expires_at <= datetime.now(UTC) + REFRESH_SKEW:
        return _refresh_and_persist(recruiter)
    return decrypt_token(recruiter.google_access_token)


def _refresh_and_persist(recruiter: Recruiter) -> str:
    """Refresh the access token and persist it in its own short-lived session —
    never the caller's — so a caller mid-transaction (e.g. US-12 creating a
    submission before an upload) can't have this write rolled back with it,
    and so a real Google refresh call is never silently undone.

    Also updates the passed-in `recruiter` object's attributes in memory
    (without touching the caller's session) so that a caller making several
    google_call()s with the same Recruiter instance in one request sees the
    refreshed state and doesn't refresh again on every subsequent call.
    """
    refresh_token = decrypt_token(recruiter.google_refresh_token)  # type: ignore[arg-type]
    response = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )

    if response.status_code == 400 and response.json().get("error") == "invalid_grant":
        with SessionLocal() as db:
            db_recruiter = db.get(Recruiter, recruiter.recruiter_id)
            assert db_recruiter is not None
            db_recruiter.account_state = RecruiterState.REAUTH_REQUIRED
            db.commit()
        recruiter.account_state = RecruiterState.REAUTH_REQUIRED
        raise ReauthRequired()

    response.raise_for_status()
    body = response.json()
    new_access_token: str = body["access_token"]
    expires_at = datetime.now(UTC) + timedelta(seconds=body["expires_in"])

    with SessionLocal() as db:
        db_recruiter = db.get(Recruiter, recruiter.recruiter_id)
        assert db_recruiter is not None
        db_recruiter.google_access_token = encrypt_token(new_access_token)
        db_recruiter.google_token_expires_at = expires_at
        db.commit()

    recruiter.google_access_token = encrypt_token(new_access_token)
    recruiter.google_token_expires_at = expires_at

    return new_access_token


def _log_usage(recruiter_id: uuid.UUID, api_name: ApiName, call_count: int) -> None:
    with SessionLocal() as db:
        db.add(ApiUsageLog(recruiter_id=recruiter_id, api_name=api_name, call_count=call_count))
        db.commit()
