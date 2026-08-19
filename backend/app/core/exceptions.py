class ReauthRequired(Exception):
    """Raised by adapters/google/session.py when the recruiter must re-consent."""


class JobNotAccepting(Exception):
    """Raised by job_service.assert_job_accepting when a job is DRAFT-excluded
    but not currently accepting applications (CLOSED, paused, or expired).
    A domain exception rather than HTTPException so the check stays callable
    from a route, a Celery task, or a script without importing FastAPI —
    same reasoning as ReauthRequired."""

    def __init__(self, job_title: str, reason: str) -> None:
        self.job_title = job_title
        self.reason = reason
        super().__init__(f"Job '{job_title}' is not accepting applications ({reason}).")
