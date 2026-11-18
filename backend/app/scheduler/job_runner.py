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
        session_maker = None,
    ):
        self.notification_service = notification_service or NotificationService()
        self.interval_seconds = interval_seconds
        self.session_maker = session_maker or async_session_maker
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

        async with self.session_maker() as session:
            notification_repo = NotificationRepository(session)
            assignment_repo = AssignmentRepository(session)
            settings_repo = SettingsRepository(session)

            # 0. Recover any notifications stuck in CLAIMED status from previous crashes
            recovered_count = await notification_repo.recover_stale_claimed(stale_threshold_seconds=300)
            if recovered_count > 0:
                logger.info(f"Recovered {recovered_count} stale claimed notifications back to PENDING.")
                await session.commit()

            # 1. Claim due notifications atomically (commits CLAIMED state so DB locks are released)
            claimed_notifications = await notification_repo.claim_due_notifications(now_utc)
            await session.commit()

            # 2. Execute claimed notifications (reminders, publications, digests, updates)
            for notif in claimed_notifications:
                logger.info(f"Executing notification {notif.id} ({notif.notification_type})")
                try:
                    await self.notification_service.execute_notification(
                        notification=notif,
                        notification_repo=notification_repo,
                        assignment_repo=assignment_repo,
                    )
                except Exception as e:
                    logger.error(f"Error executing claimed notification {notif.id}: {e}")
                    await notification_repo.mark_failed(notif.id, str(e))
                await session.commit()

            # 3. Check if weekly Sunday digest should be queued
            # Standard schedule: Sunday (weekday == 6) at or after WEEKLY_DIGEST_TIME
            # Catch-up schedule: Monday (weekday == 0) before 12:00 PM if missed due to downtime
            target_hour, target_minute = [int(p) for p in settings.WEEKLY_DIGEST_TIME.split(":")]
            is_sunday_due = (
                now_local.weekday() == 6
                and (
                    now_local.hour > target_hour
                    or (now_local.hour == target_hour and now_local.minute >= target_minute)
                )
            )
            is_monday_catchup = (
                now_local.weekday() == 0
                and now_local.hour < 12
            )

            if is_sunday_due or is_monday_catchup:
                week_key = f"weekly_digest_sent_{now_local.strftime('%Y_%U')}"
                already_sent = await settings_repo.get(week_key)

                if not already_sent:
                    mode = "catch-up" if is_monday_catchup else "scheduled"
                    logger.info(f"Queuing {mode} weekly digest for week {now_local.strftime('%Y_%U')}")
                    await notification_repo.create_notification(
                        notification_type=NotificationType.WEEKLY_DIGEST,
                        target_jid=settings.CLASS_GROUP_JID,
                        scheduled_for=now_utc,
                    )
                    await settings_repo.set(week_key, "true", description="Tracks if weekly digest was sent")
                    await session.commit()
