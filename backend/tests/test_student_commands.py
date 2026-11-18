import pytest
from datetime import datetime, timezone, timedelta
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.services.student_commands.student_command_service import StudentCommandService


@pytest.mark.asyncio
async def test_student_upcoming_query(test_session):
    assign_repo = AssignmentRepository(test_session)
    student_service = StudentCommandService()

    # Create published assignment
    await assign_repo.create_assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Binary Trees",
        description="Implement binary search tree traversal",
        deadline_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
    )
    await test_session.commit()

    reply = await student_service.handle_query(
        sender_jid="student@s.whatsapp.net",
        text="/upcoming",
        assignment_repo=assign_repo,
    )

    assert "CSC 301" in reply
    assert "Binary Trees" in reply


@pytest.mark.asyncio
async def test_student_course_filter_query(test_session):
    assign_repo = AssignmentRepository(test_session)
    student_service = StudentCommandService()

    await assign_repo.create_assignment(
        course_code="ICT 305",
        course_title="Networking",
        title="Subnetting",
        description="Calculate IP subnets",
        deadline_at=datetime.now(timezone.utc) + timedelta(days=3),
        status=AssignmentStatus.PUBLISHED,
    )
    await test_session.commit()

    reply = await student_service.handle_query(
        sender_jid="student@s.whatsapp.net",
        text="/course ICT 305",
        assignment_repo=assign_repo,
    )

    assert "ICT 305" in reply
    assert "Subnetting" in reply
