import os
import json
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def get_calendar_service():
    """
    Builds an authenticated Calendar service. Credentials are loaded in this
    order so the exact same code works locally and in production:

      1. GOOGLE_TOKEN_JSON env var (the full contents of token.json as one
         line) — used in production, since most hosts wipe local files on
         every redeploy so a token.json file on disk won't survive.
      2. token.json file on disk — used for local development, generated
         once via auth_server.py.

    Expired access tokens are refreshed automatically using the stored
    refresh token, so this keeps working for weeks/months without
    re-authorizing (as long as the refresh token itself hasn't expired —
    see the deployment guide for the "Publish App" step that prevents
    Google from expiring it after 7 days).
    """
    token_json_env = os.getenv("GOOGLE_TOKEN_JSON")

    if token_json_env:
        creds = Credentials.from_authorized_user_info(json.loads(token_json_env), SCOPES)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        raise Exception(
            "Calendar is not authenticated. Run auth_server.py locally first "
            "(creates token.json), or set GOOGLE_TOKEN_JSON for production."
        )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Keep the local file in sync when we're running locally
        if not token_json_env and os.path.exists('token.json'):
            with open('token.json', 'w') as f:
                f.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)


def check_availability(date_iso: str) -> str:
    """Checks Google Calendar for busy slots on a specific date."""
    try:
        service = get_calendar_service()

        try:
            dt = datetime.datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
        except ValueError:
            clean_str = date_iso.split('.')[0].split('+')[0].split('-')[0]
            if len(clean_str) > 10:
                dt = datetime.datetime.strptime(clean_str[:19], "%Y-%m-%dT%H:%M:%S")
            else:
                dt = datetime.datetime.strptime(clean_str[:10], "%Y-%m-%d")

        start_of_day = dt.replace(hour=0, minute=0, second=0).isoformat()
        end_of_day = dt.replace(hour=23, minute=59, second=59).isoformat()

        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")

        events_result = service.events().list(
            calendarId=calendar_id, timeMin=start_of_day, timeMax=end_of_day,
            singleEvents=True, orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"The calendar is completely free on {dt.strftime('%Y-%m-%d')}."

        busy_times = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'Busy')
            busy_times.append(f"- Blocked from {start} to {end} ({summary})")

        return f"Existing events on {dt.strftime('%Y-%m-%d')}:\n" + "\n".join(busy_times)

    except Exception as e:
        print(f"❌ CALENDAR ERROR: {e}")
        return f"Failed to check availability: {str(e)}"


def book_meeting(date_time_iso: str, name: str = "User") -> str:
    """Creates a 30-minute Google Calendar meeting."""
    try:
        service = get_calendar_service()

        try:
            start_time = datetime.datetime.fromisoformat(date_time_iso.replace('Z', '+00:00'))
        except ValueError:
            clean_str = date_time_iso.split('.')[0].split('+')[0].split('-')[0]
            start_time = datetime.datetime.strptime(clean_str[:19], "%Y-%m-%dT%H:%M:%S")

        end_time = start_time + datetime.timedelta(minutes=30)

        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")

        event = {
            'summary': f'NovaVoice Demo: {name}',
            'description': 'Automated booking created via NovaVoice AI Calling Assistant.',
            'start': {'dateTime': start_time.isoformat()},
            'end': {'dateTime': end_time.isoformat()},
        }

        event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"✅ REAL CALENDAR BOOKING SUCCESS: {event_result.get('htmlLink')}")
        return f"Success! Meeting booked on Google Calendar for {name}."

    except Exception as e:
        print(f"❌ CALENDAR ERROR: {e}")
        return f"Failed to book meeting: {str(e)}"
