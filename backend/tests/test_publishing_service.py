import pytest
from datetime import datetime, timezone
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.services.assignment_publishing.publishing_service import PublishingService
from backend.app.services.deadline_management.deadline_service import DeadlineService


def test_announcement_format():
    deadline_service = DeadlineService("Africa/Lagos")
    publishing_service = PublishingService(deadline_service=deadline_service)

    assignment = Assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Implementation",
        description="Implement a stack using arrays.",
        questions=[
            "Implement a stack using arrays.",
            "Explain the operations.",
            "Provide the time complexities.",
        ],
        deadline_at=datetime(2026, 11, 23, 16, 0, 0, tzinfo=timezone.utc),
        submission_instructions="As specified by your lecturer.",
        status=AssignmentStatus.APPROVED,
    )

    formatted = publishing_service.format_announcement(assignment)

    # Check PRD section 4.6 required tokens
    assert "📚 *NEW ASSIGNMENT*" in formatted
    assert "*Course:* CSC 301 – Data Structures" in formatted
    assert "*Assignment:* Stack Implementation" in formatted
    assert "*Submission Deadline:*" in formatted
    assert "Monday, 23 November 2026, 05:00 PM WAT" in formatted
    assert "⏰ A reminder will be sent before the submission deadline." in formatted
    assert "Please start early!" in formatted


def test_update_announcement_format():
    deadline_service = DeadlineService("Africa/Lagos")
    publishing_service = PublishingService(deadline_service=deadline_service)

    assignment = Assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Implementation",
        description="Implement a stack using arrays.",
        deadline_at=datetime(2026, 11, 25, 16, 0, 0, tzinfo=timezone.utc),
        status=AssignmentStatus.UPDATED,
    )

    formatted = publishing_service.format_update_announcement(
        assignment, "Submission deadline extended to Wednesday"
    )

    assert "📢 *ASSIGNMENT UPDATE*" in formatted
    assert "*Course:* CSC 301 – Data Structures" in formatted
    assert "Wednesday, 25 November 2026" in formatted
