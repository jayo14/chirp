from datetime import datetime, timezone, timedelta
import pytz
from backend.app.services.deadline_management.deadline_service import DeadlineService


def test_parse_iso_deadline():
    service = DeadlineService("Africa/Lagos")
    utc_dt, needs_clarif = service.parse_deadline("2026-11-23 17:00")
    assert not needs_clarif
    assert utc_dt is not None

    # In Lagos (UTC+1), 17:00 is 16:00 UTC
    assert utc_dt.hour == 16
    assert utc_dt.day == 23
    assert utc_dt.month == 11
    assert utc_dt.year == 2026


def test_parse_relative_tomorrow():
    service = DeadlineService("Africa/Lagos")
    utc_dt, needs_clarif = service.parse_deadline("tomorrow")
    assert not needs_clarif
    assert utc_dt is not None


def test_parse_missing_or_ambiguous_deadline():
    service = DeadlineService("Africa/Lagos")
    utc_dt, needs_clarif = service.parse_deadline("")
    assert needs_clarif
    assert utc_dt is None

    utc_dt, needs_clarif = service.parse_deadline("sometime next month maybe")
    assert needs_clarif
    assert utc_dt is None


def test_format_deadline_display():
    service = DeadlineService("Africa/Lagos")
    # 2026-11-23 16:00 UTC is 17:00 WAT
    lagos_tz = pytz.timezone("Africa/Lagos")
    dt = lagos_tz.localize(datetime(2026, 11, 23, 17, 0, 0)).astimezone(pytz.UTC)
    formatted = service.format_deadline_for_display(dt)
    assert "Monday, 23 November 2026, 05:00 PM WAT" in formatted


def test_calculate_reminder_time():
    service = DeadlineService("Africa/Lagos")
    future_deadline = datetime.now(timezone.utc) + timedelta(days=3)
    reminder_time = service.calculate_reminder_time(future_deadline, reminder_hours=24)
    assert reminder_time is not None
    # Reminder should be 24h before deadline
    expected_diff = future_deadline - reminder_time
    assert round(expected_diff.total_seconds()) == 24 * 3600
