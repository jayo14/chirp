import asyncio
import sys
from datetime import datetime, timezone
from backend.app.core.database import async_session_maker, init_db
from backend.app.core.config import settings
from backend.app.models.assignment import AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.deadline_management.deadline_service import DeadlineService
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.app.cli [status|pending|approve|upcoming|digest] [args]")
        return

    cmd = sys.argv[1].lower()
    await init_db()

    deadline_service = DeadlineService()
    gateway_client = WhatsAppGatewayClient()
    review_service = ReviewService(gateway_client=gateway_client, deadline_service=deadline_service)

    async with async_session_maker() as session:
        assign_repo = AssignmentRepository(session)
        notif_repo = NotificationRepository(session)

        if cmd == "status":
            gw_status = await gateway_client.get_status()
            print("Chirp System Status:")
            print(f"  App Environment: {settings.APP_ENV}")
            print(f"  Timezone: {settings.TIMEZONE}")
            print(f"  Class Group: {settings.CLASS_GROUP_JID}")
            print(f"  WhatsApp Gateway: {gw_status}")

        elif cmd == "pending":
            pending = await assign_repo.list_pending_reviews()
            if not pending:
                print("No assignments currently pending review.")
            else:
                print(f"Pending assignments ({len(pending)}):")
                for a in pending:
                    d_str = deadline_service.format_deadline_short(a.deadline_at)
                    print(f"  [{a.short_code}] {a.course_code}: {a.title} (Due: {d_str})")

        elif cmd == "approve":
            if len(sys.argv) < 3:
                print("Error: Specify short code or ID to approve. Example: approve A7B2")
                return
            target_id = sys.argv[2]
            success, msg = await review_service.approve_assignment(
                identifier=target_id,
                admin_jid="cli_admin",
                assignment_repo=assign_repo,
                notification_repo=notif_repo,
            )
            await session.commit()
            print(msg)

        elif cmd == "upcoming":
            now_utc = datetime.now(timezone.utc)
            upcoming = await assign_repo.list_active_upcoming(now_utc)
            if not upcoming:
                print("No upcoming assignments.")
            else:
                print(f"Active upcoming assignments ({len(upcoming)}):")
                for a in upcoming:
                    d_str = deadline_service.format_deadline_for_display(a.deadline_at)
                    print(f"  [{a.short_code}] {a.course_code} - {a.title}\n    Due: {d_str}")

        elif cmd == "digest":
            from backend.app.models.notification import NotificationType
            now_utc = datetime.now(timezone.utc)
            notif = await notif_repo.create_notification(
                notification_type=NotificationType.WEEKLY_DIGEST,
                target_jid=settings.CLASS_GROUP_JID,
                scheduled_for=now_utc,
            )
            await session.commit()
            print(f"Weekly digest notification queued successfully (ID: {notif.id})")

        else:
            print(f"Unknown CLI command: {cmd}")


if __name__ == "__main__":
    asyncio.run(main())
