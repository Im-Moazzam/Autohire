"""Seeds one fake recruiter for local manual testing (no real Google OAuth
needed) and prints a ready-to-use session cookie value.

    mise run db:seed
"""

from app.adapters.google.oauth import GoogleTokens, GoogleUserInfo
from app.core.db import SessionLocal
from app.services.auth_service import create_session_cookie, upsert_recruiter

_FAKE_TOKENS = GoogleTokens(
    access_token="fake-access-token",
    refresh_token="fake-refresh-token",
    expires_in=3600,
    granted_scopes=[
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "openid",
        "email",
        "profile",
    ],
)
_FAKE_USERINFO = GoogleUserInfo(
    sub="seed-recruiter-sub",
    email="seed-recruiter@example.com",
    name="Seed Recruiter",
    picture=None,
)


def main() -> None:
    db = SessionLocal()
    try:
        recruiter = upsert_recruiter(db, _FAKE_TOKENS, _FAKE_USERINFO)
        cookie = create_session_cookie(str(recruiter.recruiter_id))
    finally:
        db.close()

    print(f"recruiter_id: {recruiter.recruiter_id}")
    print(f"email: {recruiter.email}")
    print(f"session cookie value: {cookie}")
    print(f'\ncurl -H "Cookie: autohire_session={cookie}" http://localhost:8000/api/v1/auth/me')


if __name__ == "__main__":
    main()
