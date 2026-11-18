from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.notification import (
    ScheduledNotification,
    NotificationType,
    NotificationStatus,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_notification(
        self,
        notification_type: NotificationType,
        target_jid: str,
        scheduled_for: datetime,
        assignment_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ScheduledNotification:
        notification = ScheduledNotification(
            assignment_id=assignment_id,
            notification_type=notification_type,
            target_jid=target_jid,
            scheduled_for=scheduled_for,
            status=NotificationStatus.PENDING,
            payload=payload,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_due_notifications(self, now: datetime, limit: int = 20) -> List[ScheduledNotification]:
        stmt = (
            select(ScheduledNotification)
            .where(
                and_(
                    ScheduledNotification.status == NotificationStatus.PENDING,
                    ScheduledNotification.scheduled_for <= now,
                    ScheduledNotification.retry_count < ScheduledNotification.max_retries,
                )
            )
            .options(selectinload(ScheduledNotification.assignment))
            .order_by(ScheduledNotification.scheduled_for.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_sent(self, notification_id: str, sent_at: datetime) -> None:
        stmt = (
            update(ScheduledNotification)
            .where(ScheduledNotification.id == notification_id)
            .values(
                status=NotificationStatus.SENT,
                sent_at=sent_at,
            )
        )
        await self.session.execute(stmt)

    async def mark_failed(self, notification_id: str, error: str) -> None:
        notification = await self.session.get(ScheduledNotification, notification_id)
        if notification:
            notification.retry_count += 1
            notification.last_error = error
            if notification.retry_count >= notification.max_retries:
                notification.status = NotificationStatus.FAILED
            await self.session.flush()

    async def cancel_for_assignment(self, assignment_id: str) -> None:
        stmt = (
            update(ScheduledNotification)
            .where(
                and_(
                    ScheduledNotification.assignment_id == assignment_id,
                    ScheduledNotification.status == NotificationStatus.PENDING,
                )
            )
            .values(status=NotificationStatus.CANCELLED)
        )
        await self.session.execute(stmt)
