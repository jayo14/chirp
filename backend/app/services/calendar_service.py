from datetime import datetime, timezone
from typing import List
from backend.app.models.assignment import Assignment, AssignmentStatus


class CalendarService:
    @staticmethod
    def generate_ics(assignments: List[Assignment]) -> str:
        """
        Generates an iCalendar (RFC 5545) .ics feed from a list of active assignments.
        """
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Chirp//Class Assignment Bot//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Class Assignments",
            "X-WR-TIMEZONE:Africa/Lagos",
        ]

        now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        for a in assignments:
            if not a.deadline_at:
                continue

            dt_utc = a.deadline_at
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            else:
                dt_utc = dt_utc.astimezone(timezone.utc)

            due_stamp = dt_utc.strftime("%Y%m%dT%H%M%SZ")

            # Clean description for ICS format
            clean_desc = (a.description or "").replace("\n", "\\n").replace(",", "\\,")
            summary = f"[{a.course_code}] {a.title}"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{a.id}@chirp.bot",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{due_stamp}",
                f"DTEND:{due_stamp}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{clean_desc}",
                f"STATUS:{'CONFIRMED' if a.status == AssignmentStatus.PUBLISHED else 'TENTATIVE'}",
                "BEGIN:VALARM",
                "TRIGGER:-PT24H",
                "ACTION:DISPLAY",
                f"DESCRIPTION:Reminder: {summary} is due in 24 hours!",
                "END:VALARM",
                "END:VEVENT",
            ])

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"
