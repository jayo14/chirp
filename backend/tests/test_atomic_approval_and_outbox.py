import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from backend.app.core.config import settings
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.notification import ScheduledNotification, NotificationType, NotificationStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.notifications.notification_service import NotificationService


@pytest.mark.asyncio
async def test_atomic_approval_and_outbox_event_creation(test_session):
    assignment_repo = AssignmentRepository(test_session)
    notification_repo = NotificationRepository(test_session)

    # 1. Create assignment pending review
    assignment = await assignment_repo.create_assignment(
        course_code="CSC301",
        course_title="Operating Systems",
        title="Operating Systems Lab 1",
        description="Implement system calls",
        deadline_at=datetime.now(timezone.utc) + timedelta(days=3),
        status=AssignmentStatus.PENDING_REVIEW,
    )
    await test_session.commit()

    gateway_mock = AsyncMock()
    gateway_mock.send_text.return_value = {"success": True, "messageId": "msg_pub_123"}

    review_service = ReviewService(gateway_client=gateway_mock)

    # 2. First approval should succeed
    success, message = await review_service.approve_assignment(
        identifier=assignment.short_code,
        admin_jid="admin1@s.whatsapp.net",
        assignment_repo=assignment_repo,
        notification_repo=notification_repo,
    )
    await test_session.commit()

    assert success is True
    assert "approved and published" in message

    # Verify assignment is published
    await test_session.refresh(assignment)
    assert assignment.status == AssignmentStatus.PUBLISHED
    assert assignment.published_message_id == "msg_pub_123"

    # Verify outbox event was created and marked SENT
    stmt = select(ScheduledNotification).where(
        ScheduledNotification.assignment_id == assignment.id,
        ScheduledNotification.notification_type == NotificationType.ASSIGNMENT_PUBLICATION,
    )
    outbox_notifs = list((await test_session.execute(stmt)).scalars().all())
    assert len(outbox_notifs) == 1
    assert outbox_notifs[0].status == NotificationStatus.SENT

    # 3. Second concurrent/duplicate approval must fail due to atomic state condition
    success2, message2 = await review_service.approve_assignment(
        identifier=assignment.short_code,
        admin_jid="admin2@s.whatsapp.net",
        assignment_repo=assignment_repo,
        notification_repo=notification_repo,
    )
    assert success2 is False
    assert "cannot be approved from status 'published'" in message2

    # Verify no second outbox item was created
    outbox_notifs_after = list((await test_session.execute(stmt)).scalars().all())
    assert len(outbox_notifs_after) == 1


@pytest.mark.asyncio
async def test_approval_resilience_when_gateway_fails_immediately(test_session):
    assignment_repo = AssignmentRepository(test_session)
    notification_repo = NotificationRepository(test_session)

    assignment = await assignment_repo.create_assignment(
        course_code="MTH202",
        course_title="Linear Algebra",
        title="Linear Algebra Homework",
        description="Solve eigen problems",
        deadline_at=datetime.now(timezone.utc) + timedelta(days=2),
        status=AssignmentStatus.PENDING_REVIEW,
    )
    await test_session.commit()

    # Mock gateway failure
    failing_gateway = AsyncMock()
    failing_gateway.send_text.return_value = {"success": False, "error": "Gateway connection timeout"}

    review_service = ReviewService(gateway_client=failing_gateway)

    success, message = await review_service.approve_assignment(
        identifier=assignment.short_code,
        admin_jid="admin1@s.whatsapp.net",
        assignment_repo=assignment_repo,
        notification_repo=notification_repo,
    )
    await test_session.commit()

    # The assignment approval succeeds and is queued in the outbox
    assert success is True
    assert "queued for publication" in message

    # Verify assignment is in APPROVED state
    await test_session.refresh(assignment)
    assert assignment.status == AssignmentStatus.APPROVED

    # Verify outbox item exists and has retry scheduled
    stmt = select(ScheduledNotification).where(
        ScheduledNotification.assignment_id == assignment.id,
        ScheduledNotification.notification_type == NotificationType.ASSIGNMENT_PUBLICATION,
    )
    outbox_item = (await test_session.execute(stmt)).scalars().first()
    assert outbox_item is not None
    assert outbox_item.retry_count == 1
    assert outbox_item.status == NotificationStatus.PENDING


@pytest.mark.asyncio
async def test_outbox_claiming_and_crash_recovery(test_session):
    notification_repo = NotificationRepository(test_session)
    now_utc = datetime.now(timezone.utc)

    # Create a pending notification due now
    notif = await notification_repo.create_notification(
        notification_type=NotificationType.WEEKLY_DIGEST,
        target_jid="group@g.us",
        scheduled_for=now_utc - timedelta(minutes=1),
    )
    await test_session.commit()

    # Claim due notifications
    claimed = await notification_repo.claim_due_notifications(now_utc)
    assert len(claimed) == 1
    assert claimed[0].id == notif.id
    assert claimed[0].status == NotificationStatus.CLAIMED

    # Simulate worker crash: notification is left in CLAIMED status
    # Test recovery when updated_at is older than threshold
    stale_time = now_utc - timedelta(minutes=10)
    notif_in_db = await test_session.get(ScheduledNotification, notif.id)
    notif_in_db.updated_at = stale_time
    await test_session.commit()

    recovered_count = await notification_repo.recover_stale_claimed(stale_threshold_seconds=300)
    assert recovered_count == 1

    await test_session.refresh(notif_in_db)
    assert notif_in_db.status == NotificationStatus.PENDING
