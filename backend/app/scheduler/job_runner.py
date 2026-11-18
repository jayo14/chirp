import asyncio
import logging
from datetime import datetime, timezone
import pytz
from backend.app.core.config import settings
from backend.app.core.database import async_session_maker
from backend.app.models.notification import NotificationType
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.repositories.settings_repo import SettingsRepository
from backend.app.services.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(
        self,
        notification_service: NotificationService = None,
        interval_seconds: int = settings.SCHEDULER_INTERVAL_SECONDS,
    ):
        self.notification_service = notification_service or NotificationService()
        self.interval_seconds = interval_seconds
        self.running = False
        self._task: asyncio.Task = None
        self.tz = pytz.timezone(settings.TIMEZONE)

    async def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Persistent notification scheduler started (polling every {self.interval_seconds}s)")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler service stopped.")

    async def _run_loop(self):
        while self.running:
            try:
                await self.tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {str(e)}", exc_info=True)

            await asyncio.sleep(self.interval_seconds)

    async def tick(self):
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(self.tz)

        async with async_session_maker() as session:
            notification_repo = NotificationRepository(session)
            assignment_repo = AssignmentRepository(session)
            settings_repo = SettingsRepository(session)

            # 1. Process due pending notifications (reminders, digests, updates)
            due_notifications = await notification_repo.get_due_notifications(now_utc)
            for notif in due_notifications:
                logger.info(f"Processing due notification {notif.id} ({notif.notification_type})")
                await self.notification_service.execute_notification(
                    notification=notif,
                    notification_repo=notification_repo,
                    assignment_repo=assignment_repo,
                )
                await session.commit()

            # 2. Check if weekly Sunday digest should be queued
            # Sunday is weekday() == 6
            if now_local.weekday() == 6:
                target_hour, target_minute = [int(p) for p in settings.WEEKLY_DIGEST_TIME.split(":")]
                if now_local.hour == target_hour and now_local.minute >= target_minute:
                    week_key = f"weekly_digest_sent_{now_local.strftime('%Y_%U')}"
                    already_sent = await settings_repo.get(week_key)

                    if not already_sent:
                        logger.info(f"Queuing weekly digest for week {now_local.strftime('%Y_%U')}")
                        await notification_repo.create_notification(
                            notification_type=NotificationType.WEEKLY_DIGEST,
                            target_jid=settings.CLASS_GROUP_JID,
                            scheduled_for=now_utc,
                        )
                        await settings_repo.set(week_key, "true", description="Tracks if Sunday digest was sent")
                        await session.commit()
