import pytest
from datetime import datetime, timezone
from unittest.mock import patch
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


@pytest.mark.asyncio
async def test_sunday_after_target_hour_queues_weekly_digest(test_engine, test_session, mock_gateway_client):
    import pytz
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from backend.app.core.config import settings
    from backend.app.scheduler.job_runner import SchedulerService
    from backend.app.models.notification import ScheduledNotification, NotificationType

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    scheduler = SchedulerService(session_maker=session_factory)
    # Sunday at 21:30 WAT (Africa/Lagos) -> 20:30 UTC
    tz = pytz.timezone("Africa/Lagos")
    sunday_2130 = tz.localize(datetime(2026, 11, 22, 21, 30, 0))

    # Mock datetime.now in job_runner tick
    with patch("backend.app.scheduler.job_runner.datetime") as mock_dt:
        mock_dt.now.return_value = sunday_2130.astimezone(timezone.utc)
        await scheduler.tick()

    # Verify notification queued
    stmt = select(ScheduledNotification).where(
        ScheduledNotification.notification_type == NotificationType.WEEKLY_DIGEST
    )
    res = list((await test_session.execute(stmt)).scalars().all())
    assert len(res) == 1
    assert res[0].target_jid == settings.CLASS_GROUP_JID


@pytest.mark.asyncio
async def test_monday_catchup_weekly_digest(test_engine, test_session, mock_gateway_client):
    import pytz
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from backend.app.core.config import settings
    from backend.app.scheduler.job_runner import SchedulerService
    from backend.app.models.notification import ScheduledNotification, NotificationType

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    scheduler = SchedulerService(session_maker=session_factory)
    # Monday at 09:15 AM WAT (Africa/Lagos)
    tz = pytz.timezone("Africa/Lagos")
    monday_0915 = tz.localize(datetime(2026, 11, 23, 9, 15, 0))

    with patch("backend.app.scheduler.job_runner.datetime") as mock_dt:
        mock_dt.now.return_value = monday_0915.astimezone(timezone.utc)
        await scheduler.tick()

    stmt = select(ScheduledNotification).where(
        ScheduledNotification.notification_type == NotificationType.WEEKLY_DIGEST
    )
    res = list((await test_session.execute(stmt)).scalars().all())
    assert len(res) == 1


@pytest.mark.asyncio
async def test_past_deadline_assignments_transition_to_overdue(test_engine, test_session, mock_gateway_client):
    from datetime import timedelta
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from backend.app.repositories.assignment_repo import AssignmentRepository
    from backend.app.scheduler.job_runner import SchedulerService

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    scheduler = SchedulerService(session_maker=session_factory)
    assign_repo = AssignmentRepository(test_session)

    # 1. Create published assignment with deadline in the past
    now_utc = datetime.now(timezone.utc)
    assignment = await assign_repo.create_assignment(
        course_code="CSC 401",
        course_title="Distributed Systems",
        title="Past Lab",
        description="Implement Raft",
        deadline_at=now_utc - timedelta(hours=2),
        status=AssignmentStatus.PUBLISHED,
    )
    # 2. Create another published assignment with deadline in the future
    future_assign = await assign_repo.create_assignment(
        course_code="CSC 402",
        course_title="Computer Security",
        title="Future Lab",
        description="Implement RSA",
        deadline_at=now_utc + timedelta(days=2),
        status=AssignmentStatus.PUBLISHED,
    )
    await test_session.commit()

    # Trigger scheduler tick
    await scheduler.tick()

    # Verify past assignment transitioned to OVERDUE
    await test_session.refresh(assignment)
    assert assignment.status == AssignmentStatus.OVERDUE

    # Verify future assignment remains PUBLISHED
    await test_session.refresh(future_assign)
    assert future_assign.status == AssignmentStatus.PUBLISHED

