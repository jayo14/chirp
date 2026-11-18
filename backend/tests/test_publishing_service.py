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


@pytest.mark.asyncio
async def test_publish_assignment_with_local_attachment(test_session, mock_gateway_client, tmp_path):
    from backend.app.models.attachment import Attachment
    from backend.app.integrations.storage.local import LocalStorageProvider
    from backend.app.repositories.assignment_repo import AssignmentRepository
    from backend.app.repositories.notification_repo import NotificationRepository

    storage = LocalStorageProvider(base_dir=str(tmp_path))
    file_bytes = b"sample assignment pdf document content"
    file_url, storage_path = await storage.save_file(file_bytes, "csc301.pdf", "application/pdf")

    assign_repo = AssignmentRepository(test_session)
    notif_repo = NotificationRepository(test_session)

    assignment = await assign_repo.create_assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Task",
        description="Stack task description",
        deadline_at=datetime.now(timezone.utc),
        status=AssignmentStatus.APPROVED,
    )

    attachment = Attachment(
        assignment_id=assignment.id,
        file_name="csc301.pdf",
        file_url=file_url,
        storage_path=storage_path,
        mime_type="application/pdf",
        file_size=len(file_bytes),
    )
    test_session.add(attachment)
    await test_session.commit()
    # Reload assignment with attachments
    assignment = await assign_repo.get_by_id(assignment.id)

    publishing_service = PublishingService(
        gateway_client=mock_gateway_client,
        storage_provider=storage,
    )

    success = await publishing_service.publish_assignment(
        assignment=assignment,
        assignment_repo=assign_repo,
        notification_repo=notif_repo,
    )

    assert success is True
    # Verify gateway_client.send_media was called
    assert mock_gateway_client.send_media.called
    call_kwargs = mock_gateway_client.send_media.call_args.kwargs
    # mediaBase64 must be populated and file_url must be None for local file
    assert call_kwargs["media_base64"] is not None
    assert call_kwargs["file_url"] is None
    assert call_kwargs["media_type"] == "document"
    assert call_kwargs["file_name"] == "csc301.pdf"


@pytest.mark.asyncio
async def test_publish_assignment_missing_attachment_raises(test_session, mock_gateway_client, tmp_path):
    from backend.app.models.attachment import Attachment
    from backend.app.integrations.storage.local import LocalStorageProvider
    from backend.app.repositories.assignment_repo import AssignmentRepository
    from backend.app.repositories.notification_repo import NotificationRepository

    storage = LocalStorageProvider(base_dir=str(tmp_path))
    assign_repo = AssignmentRepository(test_session)
    notif_repo = NotificationRepository(test_session)

    assignment = await assign_repo.create_assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Task",
        description="Stack task description",
        status=AssignmentStatus.APPROVED,
    )

    # Missing file path that doesn't exist
    attachment = Attachment(
        assignment_id=assignment.id,
        file_name="missing.pdf",
        file_url=f"file://{tmp_path}/nonexistent.pdf",
        storage_path=f"{tmp_path}/nonexistent.pdf",
        mime_type="application/pdf",
    )
    test_session.add(attachment)
    await test_session.commit()
    assignment = await assign_repo.get_by_id(assignment.id)

    publishing_service = PublishingService(
        gateway_client=mock_gateway_client,
        storage_provider=storage,
    )

    with pytest.raises(ValueError, match="file content not found"):
        await publishing_service.publish_assignment(
            assignment=assignment,
            assignment_repo=assign_repo,
            notification_repo=notif_repo,
        )
