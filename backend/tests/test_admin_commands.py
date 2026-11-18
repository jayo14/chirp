import pytest
from datetime import datetime, timezone
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
