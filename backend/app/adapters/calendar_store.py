import uuid
from datetime import datetime, timedelta

from app.adapters.base import CalendarEvent, CalendarStore
from app.adapters.google.session import google_call
from app.core.config import settings
from app.models.api_usage_log import ApiName
from app.models.recruiter import Recruiter

CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class LocalCalendarStore:
    def create_event(
        self,
        recruiter: Recruiter,
        *,
        summary: str,
        description: str,
        starts_at: datetime,
        duration_minutes: int,
        attendee_email: str,
    ) -> CalendarEvent:
        del recruiter, summary, description, starts_at, duration_minutes, attendee_email
        event_id = f"local-{uuid.uuid4().hex}"
        return CalendarEvent(event_id=event_id, meet_link=f"https://meet.local.test/{event_id}")


class GoogleCalendarStore:
    def create_event(
        self,
        recruiter: Recruiter,
        *,
        summary: str,
        description: str,
        starts_at: datetime,
        duration_minutes: int,
        attendee_email: str,
    ) -> CalendarEvent:
        ends_at = starts_at + timedelta(minutes=duration_minutes)
        response = google_call(
            recruiter,
            ApiName.GOOGLE_CALENDAR,
            "POST",
            f"{CALENDAR_EVENTS_URL}?conferenceDataVersion=1",
            json={
                "summary": summary,
                "description": description,
                "start": {"dateTime": starts_at.isoformat()},
                "end": {"dateTime": ends_at.isoformat()},
                "attendees": [{"email": attendee_email}],
                "conferenceData": {
                    "createRequest": {
                        "requestId": uuid.uuid4().hex,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            },
        )
        data = response.json()
        meet_link = None
        for entry_point in data.get("conferenceData", {}).get("entryPoints", []):
            if entry_point.get("entryPointType") == "video":
                meet_link = entry_point.get("uri")
                break
        return CalendarEvent(event_id=data["id"], meet_link=meet_link)


def get_calendar_store() -> CalendarStore:
    if settings.app_env == "local":
        return LocalCalendarStore()
    return GoogleCalendarStore()
