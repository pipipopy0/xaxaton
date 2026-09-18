import requests
import base64
import uuid
import os

from services.calendars.ical_builder import build_ical_event

class CalDAVService:
    def __init__(self,email, password, calendar_url):
        self.email = email 
        self.password = password
        self.calendar_url = calendar_url

    def _authorize_headers(self):
        credentials = f"{self.email}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers_put = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "text/calendar; charset=utf-8"
        }

        return headers_put

    def create_calendar_event(self, event_data, reminder_offset_minutes=None):
        event_uid = str(uuid.uuid4())

        ics_content = build_ical_event(
            event_data=event_data, 
            event_uid=event_uid,
            reminder_offset_minutes=reminder_offset_minutes
            )
        event_url = self.calendar_url + f"{event_uid}.ics"

        response = requests.put(
            event_url,
            headers=self._authorize_headers(),
            data=ics_content.encode("utf-8")
        ) 

        
        if response.status_code not in (201,204):
            raise Exception(response.text)
        
        return {
            "uid" : event_uid,
            "url" : event_url
        }
    def update_event(self, event_url, event_uid, event_data,reminder_offset_minutes=None):


        ics = build_ical_event(
            event_data,
            event_uid,
            reminder_offset_minutes
        )


        response = requests.put(
            event_url,
            headers=self._authorize_headers(),
            data=ics.encode("utf-8")
        )


        if response.status_code not in (201, 204):
            raise Exception(response.text)
        return {
            "uid" : event_uid,
            "url" : event_url
        }


    def delete_event(self, event_url):

        response = requests.delete(
            event_url,
            headers=self._authorize_headers()
        )

        if response.status_code not in (200, 201, 204):
            raise Exception(response.text)
