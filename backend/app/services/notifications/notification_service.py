import logging
from datetime import datetime, timezone
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.notification import ScheduledNotification, NotificationType, NotificationStatus
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient
from backend.app.services.deadline_management.deadline_service import DeadlineService
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.notification_repo import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        gateway_client: Optional[WhatsAppGatewayClient] = None,
        deadline_service: Optional[DeadlineService] = None,
    ):
        self.gateway_client = gateway_client or WhatsAppGatewayClient()
        self.deadline_service = deadline_service or DeadlineService()

    def format_24h_reminder(self, assignment: Assignment) -> str:
        course_line = f"{assignment.course_code}"
        if assignment.course_title:
            course_line += f" – {assignment.course_title}"

        deadline_str = self.deadline_service.format_deadline_for_display(assignment.deadline_at)

        return (
            f"⏰ *ASSIGNMENT REMINDER*\n\n"
            f"*Course:* {course_line}\n\n"
            f"*Assignment:* {assignment.title}\n\n"
            f"*Deadline:* {deadline_str}\n\n"
            f"Don't forget to complete and submit your assignment!"
        )

    def format_weekly_digest(self, upcoming_assignments: List[Assignment]) -> str:
        if not upcoming_assignments:
            return (
                "📚 *WEEKLY ASSIGNMENT UPDATE*\n\n"
                "There are no outstanding assignments scheduled for this week! 🎉\n\n"
                "Enjoy your week and stay prepared!"
            )

        items_text = []
        for idx, assign in enumerate(upcoming_assignments):
            c_line = f"*{idx + 1}. {assign.course_code}"
            if assign.course_title:
                c_line += f" – {assign.course_title}*"
            else:
                c_line += "*"

            desc_brief = assign.description.split("\n")[0][:120].strip()
            deadline_str = self.deadline_service.format_deadline_for_display(assign.deadline_at)

            item = f"{c_line}\n\n{desc_brief}\n\nDeadline: {deadline_str}."
            items_text.append(item)

        joined_items = "\n\n".join(items_text)

        return (
            f"📚 *WEEKLY ASSIGNMENT UPDATE*\n\n"
            f"Here are the assignments you should keep track of this week.\n\n"
            f"{joined_items}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"*Don't wait until the last minute. Start early!*"
        )

    async def execute_notification(
        self,
        notification: ScheduledNotification,
        notification_repo: NotificationRepository,
        assignment_repo: AssignmentRepository,
    ) -> bool:
        try:
            if notification.notification_type == NotificationType.REMINDER_24H:
                if not notification.assignment_id:
                    await notification_repo.mark_failed(notification.id, "Missing assignment ID for reminder")
                    return False

                assignment = await assignment_repo.get_by_id(notification.assignment_id)
                if not assignment or assignment.status in [AssignmentStatus.CANCELLED, AssignmentStatus.REJECTED]:
                    await notification_repo.cancel_for_assignment(notification.assignment_id)
                    return False

                text = self.format_24h_reminder(assignment)
                res = await self.gateway_client.send_text(
                    to=notification.target_jid,
                    text=text,
                )
                if res.get("success"):
                    await notification_repo.mark_sent(notification.id, datetime.now(timezone.utc))
                    return True
                else:
                    await notification_repo.mark_failed(notification.id, res.get("error", "Gateway send failed"))
                    return False

            elif notification.notification_type == NotificationType.WEEKLY_DIGEST:
                now_utc = datetime.now(timezone.utc)
                upcoming = await assignment_repo.list_active_upcoming(now_utc)
                text = self.format_weekly_digest(upcoming)

                res = await self.gateway_client.send_text(
                    to=notification.target_jid,
                    text=text,
                )
                if res.get("success"):
                    await notification_repo.mark_sent(notification.id, datetime.now(timezone.utc))
                    return True
                else:
                    await notification_repo.mark_failed(notification.id, res.get("error", "Gateway send failed"))
                    return False

            elif notification.notification_type == NotificationType.ASSIGNMENT_UPDATE:
                payload = notification.payload or {}
                update_text = payload.get("text", "Assignment details updated.")
                res = await self.gateway_client.send_text(
                    to=notification.target_jid,
                    text=update_text,
                )
                if res.get("success"):
                    await notification_repo.mark_sent(notification.id, datetime.now(timezone.utc))
                    return True
                else:
                    await notification_repo.mark_failed(notification.id, res.get("error", "Gateway send failed"))
                    return False

            return False
        except Exception as e:
            logger.error(f"Error executing notification {notification.id}: {str(e)}")
            await notification_repo.mark_failed(notification.id, str(e))
            return False
