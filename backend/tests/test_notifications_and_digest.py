from datetime import datetime, timezone
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.services.notifications.notification_service import NotificationService
from backend.app.services.deadline_management.deadline_service import DeadlineService


def test_24h_reminder_format():
    deadline_service = DeadlineService("Africa/Lagos")
    service = NotificationService(deadline_service=deadline_service)

    assignment = Assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Implementation",
        description="Stack task",
        deadline_at=datetime(2026, 11, 23, 16, 0, 0, tzinfo=timezone.utc),
    )

    formatted = service.format_24h_reminder(assignment)

    # Check PRD section 4.8 format
    assert "⏰ *ASSIGNMENT REMINDER*" in formatted
    assert "*Course:* CSC 301 – Data Structures" in formatted
    assert "*Assignment:* Stack Implementation" in formatted
    assert "Monday, 23 November 2026, 05:00 PM WAT" in formatted
    assert "Don't forget to complete and submit your assignment!" in formatted


def test_weekly_digest_format():
    deadline_service = DeadlineService("Africa/Lagos")
    service = NotificationService(deadline_service=deadline_service)

    upcoming = [
        Assignment(
            course_code="CSC 301",
            course_title="Data Structures",
            title="Stack Implementation",
            description="Implement a stack using arrays.",
            deadline_at=datetime(2026, 11, 23, 16, 0, 0, tzinfo=timezone.utc),
        ),
        Assignment(
            course_code="CSC 309",
            course_title="Artificial Intelligence",
            title="ML Applications",
            description="Explain the applications of machine learning.",
            deadline_at=datetime(2026, 11, 24, 16, 0, 0, tzinfo=timezone.utc),
        ),
    ]

    formatted = service.format_weekly_digest(upcoming)

    # Check PRD section 4.9 format
    assert "📚 *WEEKLY ASSIGNMENT UPDATE*" in formatted
    assert "*1. CSC 301 – Data Structures*" in formatted
    assert "*2. CSC 309 – Artificial Intelligence*" in formatted
    assert "Don't wait until the last minute. Start early!" in formatted


def test_empty_weekly_digest_format():
    service = NotificationService()
    formatted = service.format_weekly_digest([])
    assert "no outstanding assignments" in formatted
