"""EMAIL_DISPATCH — one task per interview slot, enqueued only after that
slot's calendar event exists (calendar_sync_job), so a candidate can never
receive an invitation for a slot that failed to materialize.

idempotency_key = "{candidate_id}:{email_type}:{slot_id or 'none'}" with a
UNIQUE constraint on email_logs.idempotency_key doing the entire dedupe —
inserting the row and hitting IntegrityError IS a retry recognizing itself.
No application-level check is layered on top of it (story AC).

The row is claimed (inserted, committed) *before* the send is attempted, so
a crash mid-send can never risk a duplicate delivery — the trade is that a
crash in that exact window leaves an unsent PENDING row that a Celery
redelivery cannot heal (its insert hits the same IntegrityError and no-ops).
`email_logs.sent_at` is set at claim time, not delivery time, specifically
so that trade is visible: a PENDING row whose sent_at is old is a stalled
attempt, distinguishable from a genuinely in-flight one by age alone — see
EmailLog's docstring.

Slot state is never touched here: the interview exists regardless of email
outcome, and a failed send is surfaced via delivery_status, not by rolling
back the booking (TC-08).
"""

import uuid

from celery import Task
from celery.exceptions import Retry, SoftTimeLimitExceeded
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.adapters.mailer import get_mailer
from app.core.db import SessionLocal
from app.models.candidate import Candidate
from app.models.email_log import EmailLog
from app.models.interview import InterviewSlot
from app.models.job import JobPosting
from app.models.recruiter import Recruiter
from app.schemas.enums import DeliveryStatus, EmailType
from app.services.email_service import render_invite
from app.services.interview_service import get_preferences_row
from app.worker import celery_app

_RETRYABLE = (OperationalError,)


@celery_app.task(
    bind=True,
    acks_late=True,
    max_retries=3,
    soft_time_limit=60,
    retry_backoff=True,
    autoretry_for=_RETRYABLE,
)
def email_dispatch_job(self: Task, slot_id: str) -> None:
    with SessionLocal() as db:
        _run_email_dispatch(db, uuid.UUID(slot_id))


def _run_email_dispatch(db: Session, slot_id: uuid.UUID) -> None:
    slot = db.get(InterviewSlot, slot_id)
    if slot is None:
        return

    candidate = db.get(Candidate, slot.candidate_id)
    job = db.get(JobPosting, slot.job_id)
    recruiter = db.get(Recruiter, slot.recruiter_id)
    if candidate is None or job is None or recruiter is None:
        return

    pref = get_preferences_row(db, slot.recruiter_id)
    timezone = pref.timezone if pref is not None else "UTC"
    subject, body = render_invite(candidate, job, slot, timezone)

    idempotency_key = f"{slot.candidate_id}:{EmailType.INTERVIEW_INVITE.value}:{slot.slot_id}"
    log = EmailLog(
        recruiter_id=slot.recruiter_id,
        candidate_id=slot.candidate_id,
        slot_id=slot.slot_id,
        email_type=EmailType.INTERVIEW_INVITE,
        subject=subject,
        body_preview=body[:500],
        idempotency_key=idempotency_key,
        delivery_status=DeliveryStatus.PENDING,
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError:
        # Already claimed — a genuine duplicate delivery (TC-07) or an
        # earlier attempt that crashed mid-send. Either way this invocation
        # does not send again; that is the whole point of the constraint.
        db.rollback()
        return
    db.refresh(log)

    try:
        mailer = get_mailer()
        sent = mailer.send(recruiter, to=candidate.email, subject=subject, body=body)
    except (SoftTimeLimitExceeded, Retry):
        raise
    except Exception:
        log.delivery_status = DeliveryStatus.FAILED
        db.commit()
        return

    log.delivery_status = DeliveryStatus.SENT
    log.gmail_message_id = sent.message_id
    log.gmail_thread_id = sent.thread_id
    db.commit()
