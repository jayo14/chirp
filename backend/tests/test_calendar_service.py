from datetime import datetime, timezone, timedelta
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.services.calendar_service import CalendarService


def test_calendar_ics_generation():
    due = datetime.now(timezone.utc) + timedelta(days=2)
    assignment = Assignment(
        id="test-assign-uuid",
        course_code="CSC 301",
        course_title="Data Structures",
        title="AVL Tree Assignment",
        description="Implement AVL tree rotation logic",
        deadline_at=due,
        status=AssignmentStatus.PUBLISHED,
    )

    ics = CalendarService.generate_ics([assignment])
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "[CSC 301] AVL Tree Assignment" in ics
    assert "TRIGGER:-PT24H" in ics
