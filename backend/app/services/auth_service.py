import secrets
from datetime import UTC, datetime, timedelta

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.adapters.google.oauth import REQUIRED_SCOPES, GoogleTokens, GoogleUserInfo
from app.core.config import settings
from app.core.crypto import encrypt_token
from app.models.recruiter import Recruiter, RecruiterState

STATE_COOKIE = "autohire_oauth_state"
STATE_MAX_AGE = 300  # 5 minutes to complete the consent screen

SESSION_COOKIE = "autohire_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 14  # 14 days

_state_serializer = URLSafeTimedSerializer(settings.secret_key, salt="oauth-state")
_session_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")


def generate_state() -> tuple[str, str]:
    """Return (cookie_value, state_param). Both must match at the callback —
    a signed-only state doesn't stop an attacker from starting their own flow
    and tricking a victim into completing it (login CSRF)."""
    nonce = secrets.token_urlsafe(24)
    return nonce, _state_serializer.dumps(nonce)


def verify_state(cookie_nonce: str | None, state_param: str | None) -> bool:
    if not cookie_nonce or not state_param:
        return False
    try:
        signed_nonce = _state_serializer.loads(state_param, max_age=STATE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return secrets.compare_digest(signed_nonce, cookie_nonce)


def create_session_cookie(recruiter_id: str) -> str:
    return _session_serializer.dumps(recruiter_id)


def read_session_cookie(cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None
    try:
        recruiter_id: str = _session_serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return recruiter_id


def upsert_recruiter(db: Session, tokens: GoogleTokens, userinfo: GoogleUserInfo) -> Recruiter:
    granted = set(tokens.granted_scopes)
    account_state = (
        RecruiterState.ACTIVE
        if set(REQUIRED_SCOPES).issubset(granted)
        else RecruiterState.REAUTH_REQUIRED
    )
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=tokens.expires_in)

    recruiter = db.query(Recruiter).filter_by(google_user_id=userinfo.sub).one_or_none()
    if recruiter is None:
        recruiter = Recruiter(
            google_user_id=userinfo.sub,
            email=userinfo.email,
            full_name=userinfo.name,
            profile_picture_url=userinfo.picture,
            google_access_token=encrypt_token(tokens.access_token),
            google_refresh_token=(
                encrypt_token(tokens.refresh_token) if tokens.refresh_token else None
            ),
            google_token_expires_at=expires_at,
            granted_scopes=tokens.granted_scopes,
            account_state=account_state,
            created_at=now,
            last_login_at=now,
        )
        db.add(recruiter)
    else:
        recruiter.email = userinfo.email
        recruiter.full_name = userinfo.name
        recruiter.profile_picture_url = userinfo.picture
        recruiter.google_access_token = encrypt_token(tokens.access_token)
        # Google only reissues a refresh token on some re-consents; keep the
        # existing one rather than overwrite it with nothing.
        if tokens.refresh_token:
            recruiter.google_refresh_token = encrypt_token(tokens.refresh_token)
        recruiter.google_token_expires_at = expires_at
        recruiter.granted_scopes = tokens.granted_scopes
        # ponytail: overwrites SUSPENDED on login since no admin flow exists yet
        # to set it; revisit once the admin suspend story lands.
        recruiter.account_state = account_state
        recruiter.last_login_at = now

    db.commit()
    db.refresh(recruiter)
    return recruiter
