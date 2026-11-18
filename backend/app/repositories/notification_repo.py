from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.assignment import Assignment
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

    async def claim_due_notifications(
        self,
        now: datetime,
        limit: int = 20,
    ) -> List[ScheduledNotification]:
        """
        Atomically claims due pending notifications by transitioning status PENDING -> CLAIMED.
        This prevents duplicate execution by concurrent workers and avoids holding open
        database locks during external network I/O.
        """
        candidate_stmt = (
            select(ScheduledNotification.id)
            .where(
                and_(
                    ScheduledNotification.status == NotificationStatus.PENDING,
                    ScheduledNotification.scheduled_for <= now,
                    ScheduledNotification.retry_count < ScheduledNotification.max_retries,
                )
            )
            .order_by(ScheduledNotification.scheduled_for.asc())
            .limit(limit)
        )
        candidate_ids = list((await self.session.execute(candidate_stmt)).scalars().all())
        if not candidate_ids:
            return []

        claim_stmt = (
            update(ScheduledNotification)
            .where(
                and_(
                    ScheduledNotification.id.in_(candidate_ids),
                    ScheduledNotification.status == NotificationStatus.PENDING,
                )
            )
            .values(status=NotificationStatus.CLAIMED)
        )
        await self.session.execute(claim_stmt)
        await self.session.flush()

        fetch_stmt = (
            select(ScheduledNotification)
            .where(ScheduledNotification.id.in_(candidate_ids))
            .options(
                selectinload(ScheduledNotification.assignment).selectinload(Assignment.attachments)
            )
        )
        result = await self.session.execute(fetch_stmt)
        return list(result.scalars().all())

    async def recover_stale_claimed(self, stale_threshold_seconds: int = 300) -> int:
        """
        Recovers notifications that were claimed but never finished due to worker crash.
        Resets them back to PENDING if they have been CLAIMED longer than the threshold.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_seconds)
        stmt = (
            update(ScheduledNotification)
            .where(
                and_(
                    ScheduledNotification.status == NotificationStatus.CLAIMED,
                    ScheduledNotification.updated_at <= cutoff,
                )
            )
            .values(status=NotificationStatus.PENDING)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount

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
            else:
                # Exponential backoff retry: 2^retry_count * 30 seconds
                delay_seconds = (2 ** notification.retry_count) * 30
                notification.scheduled_for = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
                notification.status = NotificationStatus.PENDING
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
