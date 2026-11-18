import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import pytz
from backend.app.core.config import settings


class DeadlineService:
    def __init__(self, timezone_name: Optional[str] = None):
        self.tz_name = timezone_name or settings.TIMEZONE or "Africa/Lagos"
        self.tz = pytz.timezone(self.tz_name)

    def parse_deadline(self, deadline_str: Optional[str]) -> Tuple[Optional[datetime], bool]:
        """
        Parses a deadline string into a UTC datetime, interpreting local time as Africa/Lagos.
        Returns: (utc_datetime, clarification_needed)
        """
        if not deadline_str or not deadline_str.strip():
            return None, True

        clean = deadline_str.strip()

        # Handle ISO format e.g. "2026-11-23T17:00:00" or "2026-11-23 17:00"
        iso_pattern = r"^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?$"
        match = re.match(iso_pattern, clean)

        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            hour = int(match.group(4)) if match.group(4) else 17  # default to 5 PM
            minute = int(match.group(5)) if match.group(5) else 0
            second = int(match.group(6)) if match.group(6) else 0

            local_dt = self.tz.localize(datetime(year, month, day, hour, minute, second))
            utc_dt = local_dt.astimezone(pytz.UTC)
            return utc_dt, False

        # Handle "Tomorrow" or relative words
        now_local = datetime.now(self.tz)
        clean_lower = clean.lower()

        if "tomorrow" in clean_lower:
            target = now_local + timedelta(days=1)
            local_dt = self.tz.localize(datetime(target.year, target.month, target.day, 17, 0, 0))
            return local_dt.astimezone(pytz.UTC), False

        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for idx, day_name in enumerate(days_of_week):
            if day_name in clean_lower:
                days_ahead = (idx - now_local.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target = now_local + timedelta(days=days_ahead)
                local_dt = self.tz.localize(datetime(target.year, target.month, target.day, 17, 0, 0))
                return local_dt.astimezone(pytz.UTC), False

        # If unable to parse deterministically, flag for clarification
        return None, True

    def format_deadline_for_display(self, utc_dt: Optional[datetime]) -> str:
        """
        Formats UTC datetime for student-facing announcements in Africa/Lagos timezone.
        Example: "Monday, 23 November 2026, 5:00 PM WAT" or "TBD (Clarification needed)"
        """
        if not utc_dt:
            return "To be announced / Clarification needed"

        if utc_dt.tzinfo is None:
            utc_dt = pytz.UTC.localize(utc_dt)
        else:
            utc_dt = utc_dt.astimezone(pytz.UTC)

        local_dt = utc_dt.astimezone(self.tz)
        return local_dt.strftime("%A, %d %B %Y, %I:%M %p WAT")

    def format_deadline_short(self, utc_dt: Optional[datetime]) -> str:
        if not utc_dt:
            return "TBD"

        if utc_dt.tzinfo is None:
            utc_dt = pytz.UTC.localize(utc_dt)
        else:
            utc_dt = utc_dt.astimezone(pytz.UTC)

        local_dt = utc_dt.astimezone(self.tz)
        return local_dt.strftime("%A, %d %b, %I:%M %p")

    def calculate_reminder_time(
        self,
        deadline_utc: datetime,
        reminder_hours: int = settings.DEFAULT_REMINDER_HOURS,
    ) -> Optional[datetime]:
        """
        Calculates when the reminder should be sent (typically 24 hours before deadline).
        If the reminder time is already in the past, returns now + 5 minutes.
        """
        if not deadline_utc:
            return None

        if deadline_utc.tzinfo is None:
            deadline_utc = pytz.UTC.localize(deadline_utc)

        reminder_utc = deadline_utc - timedelta(hours=reminder_hours)
        now_utc = datetime.now(timezone.utc)

        if reminder_utc <= now_utc:
            # If deadline is very soon (e.g. within 24h), send reminder shortly if deadline is still in future
            if deadline_utc > now_utc:
                return now_utc + timedelta(minutes=2)
            return None

        return reminder_utc
