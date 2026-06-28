"""Google Calendar integration for clinician check-in scheduling.

When Google Calendar credentials are configured, check-ins sync automatically.
When not configured, everything works locally without sync.
"""
import os
import json
from pathlib import Path
from clinic.config import GOOGLE_CALENDAR_CREDENTIALS_PATH, GOOGLE_CALENDAR_TOKEN_PATH

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_google_calendar_service(clinician_id: str):
    """Get authenticated Google Calendar API service. Returns None if not configured."""
    if not HAS_GOOGLE or not GOOGLE_CALENDAR_CREDENTIALS_PATH:
        return None

    creds = None
    token_path = Path(GOOGLE_CALENDAR_TOKEN_PATH)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif Path(GOOGLE_CALENDAR_CREDENTIALS_PATH).exists():
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CALENDAR_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            return None

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    service,
    summary: str,
    description: str,
    start_datetime: str,
    end_datetime: str,
    attendee_email: str | None = None,
) -> str | None:
    """Create a Google Calendar event. Returns the event ID or None."""
    if not service:
        return None

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": "America/Los_Angeles"},
        "end": {"dateTime": end_datetime, "timeZone": "America/Los_Angeles"},
    }

    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]

    try:
        result = service.events().insert(calendarId="primary", body=event).execute()
        return result.get("id")
    except Exception:
        return None


def delete_calendar_event(service, event_id: str) -> bool:
    """Delete a Google Calendar event."""
    if not service or not event_id:
        return False
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return True
    except Exception:
        return False
