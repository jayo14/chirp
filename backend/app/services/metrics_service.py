from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.source import AssignmentSource
from backend.app.models.notification import ScheduledNotification, NotificationStatus, NotificationType


class MetricsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_metrics_summary(self) -> dict:
        # Total assignments
        total_assignments_stmt = select(func.count(Assignment.id))
        total_assignments = (await self.session.execute(total_assignments_stmt)).scalar() or 0

        # Assignments by status
        published_stmt = select(func.count(Assignment.id)).where(Assignment.status == AssignmentStatus.PUBLISHED)
        published_count = (await self.session.execute(published_stmt)).scalar() or 0

        pending_stmt = select(func.count(Assignment.id)).where(Assignment.status == AssignmentStatus.PENDING_REVIEW)
        pending_count = (await self.session.execute(pending_stmt)).scalar() or 0

        rejected_stmt = select(func.count(Assignment.id)).where(Assignment.status == AssignmentStatus.REJECTED)
        rejected_count = (await self.session.execute(rejected_stmt)).scalar() or 0

        # Total source messages processed
        total_sources_stmt = select(func.count(AssignmentSource.id))
        total_sources = (await self.session.execute(total_sources_stmt)).scalar() or 0

        # Notifications stats
        reminders_sent_stmt = select(func.count(ScheduledNotification.id)).where(
            ScheduledNotification.notification_type == NotificationType.REMINDER_24H,
            ScheduledNotification.status == NotificationStatus.SENT,
        )
        reminders_sent = (await self.session.execute(reminders_sent_stmt)).scalar() or 0

        reminders_pending_stmt = select(func.count(ScheduledNotification.id)).where(
            ScheduledNotification.notification_type == NotificationType.REMINDER_24H,
            ScheduledNotification.status == NotificationStatus.PENDING,
        )
        reminders_pending = (await self.session.execute(reminders_pending_stmt)).scalar() or 0

        reminders_failed_stmt = select(func.count(ScheduledNotification.id)).where(
            ScheduledNotification.notification_type == NotificationType.REMINDER_24H,
            ScheduledNotification.status == NotificationStatus.FAILED,
        )
        reminders_failed = (await self.session.execute(reminders_failed_stmt)).scalar() or 0

        total_due_reminders = reminders_sent + reminders_failed
        reminder_delivery_rate = 100.0 if total_due_reminders == 0 else round((reminders_sent / total_due_reminders) * 100.0, 1)

        # Duplicate check: check if any published message ID appears more than once
        dup_stmt = (
            select(Assignment.published_message_id, func.count(Assignment.id))
            .where(Assignment.published_message_id.is_not(None))
            .group_by(Assignment.published_message_id)
            .having(func.count(Assignment.id) > 1)
        )
        duplicate_publications = len((await self.session.execute(dup_stmt)).all())

        return {
            "assignments": {
                "total_detected": total_assignments,
                "published": published_count,
                "pending_review": pending_count,
                "rejected": rejected_count,
            },
            "delivery_reliability": {
                "reminder_delivery_rate_percent": reminder_delivery_rate,
                "reminders_sent": reminders_sent,
                "reminders_pending": reminders_pending,
                "reminders_failed": reminders_failed,
                "duplicate_publications": duplicate_publications,
            },
            "traffic": {
                "total_source_messages_ingested": total_sources,
            },
        }
