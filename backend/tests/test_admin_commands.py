import pytest
from datetime import datetime, timezone
from backend.app.core.config import settings
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.admin_commands.command_service import AdminCommandService
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.assignment_publishing.publishing_service import PublishingService


@pytest.mark.asyncio
async def test_unauthorized_sender(test_session, mock_gateway_client):
    cmd_service = AdminCommandService()
    assign_repo = AssignmentRepository(test_session)
    admin_repo = AdminRepository(test_session)
    notif_repo = NotificationRepository(test_session)

    res = await cmd_service.handle_command(
        sender_jid="unknown_student@s.whatsapp.net",
        text="/pending",
        assignment_repo=assign_repo,
        admin_repo=admin_repo,
        notification_repo=notif_repo,
    )

    assert "not authorized" in res.lower()


@pytest.mark.asyncio
async def test_admin_help_and_pending(test_session, mock_gateway_client):
    admin_jid = "2348012345678@s.whatsapp.net"
    assign_repo = AssignmentRepository(test_session)
    admin_repo = AdminRepository(test_session)
    notif_repo = NotificationRepository(test_session)
    await admin_repo.add_admin(admin_jid, name="Class Rep")

    review_service = ReviewService(gateway_client=mock_gateway_client)
    cmd_service = AdminCommandService(review_service=review_service)

    # Test /help
    help_res = await cmd_service.handle_command(
        sender_jid=admin_jid,
        text="/help",
        assignment_repo=assign_repo,
        admin_repo=admin_repo,
        notification_repo=notif_repo,
    )
    assert "/pending" in help_res
    assert "/approve" in help_res

    # Create pending assignment
    assignment = await assign_repo.create_assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Task",
        description="Stack task description",
        deadline_at=datetime.now(timezone.utc),
    )
    await test_session.commit()

    # Test /pending
    pending_res = await cmd_service.handle_command(
        sender_jid=admin_jid,
        text="/pending",
        assignment_repo=assign_repo,
        admin_repo=admin_repo,
        notification_repo=notif_repo,
    )
    assert assignment.short_code in pending_res
    assert "CSC 301" in pending_res

    # Test /approve
    approve_res = await cmd_service.handle_command(
        sender_jid=admin_jid,
        text=f"/approve {assignment.short_code}",
        assignment_repo=assign_repo,
        admin_repo=admin_repo,
        notification_repo=notif_repo,
    )
    assert "approved and published" in approve_res
    await test_session.refresh(assignment)
    assert assignment.status == AssignmentStatus.PUBLISHED


@pytest.mark.asyncio
async def test_admin_edit_draft_assignment_with_quotes(test_session, mock_gateway_client):
    admin_jid = "2348012345678@s.whatsapp.net"
    assign_repo = AssignmentRepository(test_session)
    admin_repo = AdminRepository(test_session)
    notif_repo = NotificationRepository(test_session)
    await admin_repo.add_admin(admin_jid, name="Class Rep")

    review_service = ReviewService(gateway_client=mock_gateway_client)
    cmd_service = AdminCommandService(review_service=review_service)

    assignment = await assign_repo.create_assignment(
        course_code="CSC 301",
        course_title="Operating Systems",
        title="Initial Draft Title",
        description="Initial description",
        deadline_at=datetime.now(timezone.utc),
        status=AssignmentStatus.PENDING_REVIEW,
    )
    await test_session.commit()

    edit_cmd = (
        f'/edit {assignment.short_code} '
        f'title="Advanced Operating Systems Project" '
        f'course="CSC 305" '
        f'desc="Build a round-robin scheduler in C" '
        f'instructions="Submit ZIP archive on LMS" '
        f'deadline="2026-12-10 23:59"'
    )

    res = await cmd_service.handle_command(
        sender_jid=admin_jid,
        text=edit_cmd,
        assignment_repo=assign_repo,
        admin_repo=admin_repo,
        notification_repo=notif_repo,
    )

    assert "updated" in res.lower()
    await test_session.refresh(assignment)
    assert assignment.title == "Advanced Operating Systems Project"
    assert assignment.course_code == "CSC 305"
    assert assignment.description == "Build a round-robin scheduler in C"
    assert assignment.submission_instructions == "Submit ZIP archive on LMS"
    assert assignment.status == AssignmentStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_admin_edit_published_assignment_broadcasts_update(test_session, mock_gateway_client):
    admin_jid = "2348012345678@s.whatsapp.net"
    assign_repo = AssignmentRepository(test_session)
    admin_repo = AdminRepository(test_session)
    notif_repo = NotificationRepository(test_session)
    await admin_repo.add_admin(admin_jid, name="Class Rep")

    review_service = ReviewService(gateway_client=mock_gateway_client)
    cmd_service = AdminCommandService(review_service=review_service)

    assignment = await assign_repo.create_assignment(
        course_code="CSC 401",
        course_title="Distributed Systems",
        title="Consensus Lab",
        description="Implement Raft",
        deadline_at=datetime.now(timezone.utc),
        status=AssignmentStatus.PUBLISHED,
    )
    await test_session.commit()

    edit_cmd = f'/edit {assignment.short_code} deadline="2026-12-15 12:00"'

    res = await cmd_service.handle_command(
        sender_jid=admin_jid,
        text=edit_cmd,
        assignment_repo=assign_repo,
        admin_repo=admin_repo,
        notification_repo=notif_repo,
    )

    assert "updated" in res.lower()
    await test_session.refresh(assignment)
    assert assignment.status == AssignmentStatus.UPDATED

    # Verify broadcast message was sent to class group
    assert mock_gateway_client.send_text.called
    calls = [c[1] for c in mock_gateway_client.send_text.call_args_list]
    broadcast_call = next((c for c in calls if "ASSIGNMENT UPDATE" in c.get("text", "")), None)
    assert broadcast_call is not None
    assert broadcast_call["to"] == settings.CLASS_GROUP_JID
    assert "Consensus Lab" in broadcast_call["text"]
