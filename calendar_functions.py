import datetime
import pytz
import os.path
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


CAL_ID = "e4268e6b257004345cf2a5b26515f9b91990398cf481d66a8835a2d26711803e@group.calendar.google.com"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "Europe/London"


def get_calendar_service():
    """Builds and returns the authenticated Google Calendar API service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def create_event(
    summary: str,
    start_time: str,  # Expected format: "YYYY-MM-DDTHH:MM:SS"
    end_time: Optional[str] = None,    # Expected format: "YYYY-MM-DDTHH:MM:SS"
    location: Optional[str] = None,
    recurrence_rule: Optional[str] = None # e.g., "RRULE:FREQ=WEEKLY;BYDAY=TH"
) -> str:
    """
    Creates a single or recurring calendar event in the primary calendar.

    The LLM **MUST** convert all natural language time (e.g., '6pm today', 'tomorrow') 
    into a precise, full ISO 8601 timestamp string (e.g., 'YYYY-MM-DDTHH:MM:SS') 
    before calling this function. Do not pass ambiguous dates or recurrence rules 
    as summary or time strings.

    Args:
        summary (str): The concise title of the event (e.g., 'Supo', 'Physics Lecture').
        start_time (str): The calculated start date and time in 'YYYY-MM-DDTHH:MM:SS' format.
        end_time (Optional[str]): The calculated end date and time in 'YYYY-MM-DDTHH:MM:SS' format.
        location (Optional[str]): Physical location of the event (e.g., 'Sidney Sussex Room B6').
        recurrence_rule (Optional[str]): RRULE string for recurring events (e.g., 'RRULE:FREQ=WEEKLY;BYDAY=TH').
    """
    
    if not end_time:
      end_time = (datetime.datetime.fromisoformat(start_time) + datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')

    proposed_action = f"""
--- CONFIRMATION REQUIRED ---
Action: + ADD Event
Summary: {summary}
Time: {start_time} to {end_time}
Location: {location or 'None'}
Recurrence: {recurrence_rule or 'None'}
----------------------------
"""

    print(proposed_action)

    confirmation = input("Confirm action? (y/n): ").lower()

    if confirmation != 'y' and confirmation != '':
      return "Action cancelled by user."

    service = get_calendar_service()
    event_body = {
        'summary': summary,
        'location': location,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Europe/London',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Europe/London',
        },
        'reminders': {
            'useDefault': True,
        }
    }

    if recurrence_rule:
        event_body['recurrence'] = [recurrence_rule]

    try:
        event = service.events().insert(calendarId=CAL_ID, body=event_body).execute()
        # SUCCESS: Return a helpful message with the link
        return f"Event '{event.get('summary')}' successfully created. Check link: {event.get('htmlLink')}"
    except HttpError as error:
        # **CRUCIAL FIX:** Return the detailed error content from the API.
        # This allows the LLM to read the reason (e.g., 'Invalid date format').
        return f"API FAILURE (HTTP {error.resp.status}): {error.content.decode()}"




def delete_event_by_id(
    event_id: str,
) -> str:
    """
    Deletes a specific event by its unique ID.
    This function should be called after a search function has found the event.
    """
    service = get_calendar_service()
    try:
        service.events().delete(calendarId=CAL_ID, eventId=event_id).execute()
        print(f"Event with ID '{event_id}' has been successfully deleted.")
        return f"Event with ID '{event_id}' has been successfully deleted."
    except HttpError as error:
        return f"Error deleting event with ID '{event_id}': {error}"

def find_and_delete_events_by_summary(
    summary_query: str,
) -> str:
    """
    Searches for all upcoming events matching a specific summary query and deletes them.

    This function first identifies the master ID of any recurring events to
    delete the entire series, thereby preventing an infinite deletion loop.

    Args:
        summary_query (str): The search term used to find events (e.g., 'supo', 'meeting prep').
    """
    service = get_calendar_service()
    
    # We use a set to track master IDs we've already handled
    master_ids_deleted = set()
    events_list = []
    
    try:
        # Step 1: Search for the events, expanding recurring events
        now = datetime.datetime.now(tz=pytz.timezone(TIMEZONE)).isoformat()
        
        events_result = service.events().list(
            calendarId=CAL_ID,
            timeMin=now,
            q=summary_query,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events_to_delete = events_result.get('items', [])
        
        if not events_to_delete:
            return f"No upcoming events found matching summary '{summary_query}'."

        for event in events_to_delete:
            master_id = event.get('recurringEventId') or event.get('id')

            if master_id not in master_ids_deleted:
                delete_event_by_id(master_id)
                events_list.append(event)
                master_ids_deleted.add(master_id)

        proposed_action = f"""
--- CONFIRMATION REQUIRED ---
Action: - DELETE Events

"""

        print(event['summary'])
        for event in events_list:
            proposed_action += f"Summary: {event['summary']}\n"
            proposed_action += f"Time: {event['start']['dateTime']} to {event['end']['dateTime']}\n"
            proposed_action += f"Location: {event['location'] if 'location' in event else "None"}\n"
            proposed_action += f"Recurrence: {event['recurrence'] if 'recurrence' in event else "None"}\n\n"

        proposed_action += "----------------------------"

        print(proposed_action)
        confirmation = input("Confirm action? (y/n): ").lower()

        if confirmation != 'y' and confirmation != '':
            return "Action cancelled by user."
        
        for event in events_list:
            master_id = event.get('recurringEventId') or event.get('id')
            delete_event_by_id(master_id)

        return f"Successfully deleted events or event series matching '{summary_query}'."
             
    except HttpError as error:
        return f"Error finding and deleting events: {error}"

def list_all_calendars() -> str:
    """
    Retrieves the ID and summary of all calendars accessible by the user.

    Returns:
        A formatted string listing all accessible calendars, including their IDs.
    """
    service = get_calendar_service()
    
    try:
        # Call the CalendarList API
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])

        if not calendars:
            return "No calendars found on the user's account."

        output = "Accessible Calendars:\n"
        for calendar in calendars:
            summary = calendar.get('summary')
            calendar_id = calendar.get('id')
            is_primary = " (PRIMARY)" if calendar.get('primary') else ""
            
            output += f"- Name: {summary}{is_primary}\n  ID: {calendar_id}\n"
            
        return output
        
    except HttpError as error:
        return f"Error listing calendars: {error}"

def get_current_datetime() -> str:
    """
    Returns the current date and time in the 'YYYY-MM-DDTHH:MM:SS' format, 
    localized to Europe/London. The LLM MUST use this information to resolve 
    relative time phrases like 'today', 'tomorrow', or 'next week'.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.datetime.now(tz)
    return now.strftime("%Y-%m-%dT%H:%M:%S")


if __name__ == '__main__':
  # print(list_all_calendars())
  print(find_and_delete_events_by_summary("supo"))
  print(get_current_datetime())