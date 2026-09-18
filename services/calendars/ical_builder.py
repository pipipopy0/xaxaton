"""Собирает объект для действия с событием"""

from datetime import datetime, timedelta, timezone

def build_ical_event(event_data, event_uid=None, reminder_offset_minutes = None):

    start_time = event_data["start_at"]
    duration_min = event_data.get("duration_min", 60)
    end_time = (start_time + timedelta(minutes=duration_min))
    summary = event_data.get("text", "Событие")

    start_str = start_time.strftime("%Y%m%dT%H%M%SZ")
    end_str = end_time.strftime("%Y%m%dT%H%M%SZ")
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{start_str}",
        f"DTEND:{end_str}",
        f"SUMMARY:{summary}",
    ]
    if reminder_offset_minutes is not None and reminder_offset_minutes > 0:
        trigger = f"-PT{reminder_offset_minutes}M"
        lines.extend([
            "BEGIN:VALARM",
            f"TRIGGER:{trigger}",
            "ACTION:DISPLAY",
            "DESCRIPTION:Напоминание",
            "END:VALARM",
        ])
    lines.extend([
        "END:VEVENT",
        "END:VCALENDAR"
    ])

    return "\n".join(lines)