"""Google OAuth: authorization URL, code exchange, userinfo lookup.

Raw HTTP via httpx only — no googleapiclient, per the adapter rule.
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"

# ADR-002: the minimum functional scope set. Adding a restricted scope later
# restarts Google verification, so this list is deliberate, not exhaustive.
REQUIRED_SCOPES = (
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
)
# Unrestricted identity scopes, needed to know who signed in. Do not add
# anything else here without a new ADR.
IDENTITY_SCOPES = ("openid", "email", "profile")
REQUESTED_SCOPES = REQUIRED_SCOPES + IDENTITY_SCOPES


@dataclass
class GoogleTokens:
    access_token: str
    refresh_token: str | None
    expires_in: int
    granted_scopes: list[str]


@dataclass
class GoogleUserInfo:
    sub: str
    email: str
    name: str
    picture: str | None


def build_auth_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(REQUESTED_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code(code: str) -> GoogleTokens:
    response = httpx.post(
        TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    return GoogleTokens(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token"),
        expires_in=body["expires_in"],
        granted_scopes=body.get("scope", "").split(),
    )


def fetch_userinfo(access_token: str) -> GoogleUserInfo:
    response = httpx.get(
        USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    return GoogleUserInfo(
        sub=body["sub"],
        email=body["email"],
        name=body.get("name", body["email"]),
        picture=body.get("picture"),
    )
