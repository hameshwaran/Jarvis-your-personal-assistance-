"""
===========================================================
J.A.R.V.I.S. — Calendar Tool (Google Calendar API)
===========================================================
Read events, add events, reminders. Free tier.
===========================================================
"""

import os
import logging
from datetime import datetime, timedelta
from jarvis.config import CALENDAR_CREDENTIALS_FILE, CALENDAR_TOKEN_FILE

logger = logging.getLogger("jarvis.tools.calendar")


class CalendarTool:
    """Google Calendar integration (free tier)."""

    def __init__(self, memory=None):
        self.memory = memory
        self._service = None
        self._available = False
        if CALENDAR_CREDENTIALS_FILE and os.path.exists(str(CALENDAR_CREDENTIALS_FILE)):
            self._init_service()
        else:
            logger.info("Calendar not configured — tool disabled")

    def _init_service(self):
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            SCOPES = ["https://www.googleapis.com/auth/calendar"]
            creds = None
            if os.path.exists(str(CALENDAR_TOKEN_FILE)):
                creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(CALENDAR_CREDENTIALS_FILE), SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(str(CALENDAR_TOKEN_FILE), "w") as f:
                    f.write(creds.to_json())
            self._service = build("calendar", "v3", credentials=creds)
            self._available = True
            logger.info("Calendar API initialized")
        except Exception as e:
            logger.warning(f"Calendar init failed: {e}")

    def execute(self, params: dict) -> str:
        if not self._available:
            return "Calendar not configured, Sir. Set up Google Calendar credentials."
        action = params.get("action", "read").lower()
        if action == "read":
            return self._read_events(params)
        elif action == "add":
            return self._add_event(params)
        return f"Unknown calendar action: '{action}'"

    def _read_events(self, params):
        try:
            days = params.get("days", 1)
            now = datetime.utcnow()
            time_min = now.isoformat() + "Z"
            time_max = (now + timedelta(days=days)).isoformat() + "Z"
            result = self._service.events().list(
                calendarId="primary", timeMin=time_min, timeMax=time_max,
                maxResults=10, singleEvents=True, orderBy="startTime"
            ).execute()
            events = result.get("items", [])
            if not events:
                return "No upcoming events, Sir. Your schedule is clear."
            period = "today" if days == 1 else f"the next {days} days"
            lines = [f"Your schedule for {period}:\n"]
            for e in events:
                start = e["start"].get("dateTime", e["start"].get("date", ""))
                summary = e.get("summary", "Untitled Event")
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    time_str = dt.strftime("%I:%M %p")
                except Exception:
                    time_str = start
                lines.append(f"  • {time_str} — {summary}")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to read calendar, Sir: {e}"

    def _add_event(self, params):
        title = params.get("title", "New Event")
        time_str = params.get("time", "")
        duration = params.get("duration_minutes", 60)
        if not time_str:
            return "Please specify a time for the event, Sir."
        try:
            from dateutil import parser as dtparser
            start_dt = dtparser.parse(time_str)
            end_dt = start_dt + timedelta(minutes=duration)
            event = {
                "summary": title,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
                "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 15}]}
            }
            self._service.events().insert(calendarId="primary", body=event).execute()
            return f"Event '{title}' added at {start_dt.strftime('%I:%M %p')}, Sir."
        except ImportError:
            return "Date parsing requires python-dateutil. Install it for calendar support."
        except Exception as e:
            return f"Failed to add event, Sir: {e}"
