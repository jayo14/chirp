import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from backend.app.core.config import settings
from backend.app.models.assignment import AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.deadline_management.deadline_service import DeadlineService
from backend.app.services.assignment_publishing.publishing_service import PublishingService

logger = logging.getLogger(__name__)


class AdminCommandService:
    def __init__(
        self,
        review_service: Optional[ReviewService] = None,
        deadline_service: Optional[DeadlineService] = None,
        publishing_service: Optional[PublishingService] = None,
    ):
        self.review_service = review_service or ReviewService()
        self.deadline_service = deadline_service or DeadlineService()
        self.publishing_service = publishing_service or PublishingService()

    def is_command(self, text: str) -> bool:
        if not text:
            return False
        clean = text.strip()
        return clean.startswith("/") or clean.startswith("!")

    async def handle_command(
        self,
        sender_jid: str,
        text: str,
        assignment_repo: AssignmentRepository,
        admin_repo: AdminRepository,
        notification_repo: NotificationRepository,
    ) -> str:
        # Check authorization
        is_authorized = await admin_repo.is_admin(sender_jid, settings.admin_jid_list)
        if not is_authorized:
            return "⛔ You are not authorized to execute administrator commands."

        clean = text.strip()
        parts = clean.split()
        cmd = parts[0].lower().lstrip("/").lstrip("!")

        if cmd == "help":
            return (
                "🛠️ *CHIRP ADMIN COMMANDS*\n\n"
                "• `/pending` - View assignments waiting for approval\n"
                "• `/approve <ID>` - Approve and publish assignment\n"
                "• `/reject <ID> [reason]` - Reject assignment candidate\n"
                "• `/edit <ID> title=... deadline=YYYY-MM-DD` - Edit assignment\n"
                "• `/upcoming` - View upcoming active assignments\n"
                "• `/assignments` - List recent tracked assignments\n"
                "• `/help` - Show this help menu"
            )

        elif cmd == "pending":
            pending = await assignment_repo.list_pending_reviews()
            if not pending:
                return "✅ No assignments currently pending review."

            lines = ["📋 *PENDING ASSIGNMENTS FOR REVIEW:*\n"]
            for a in pending:
                d_str = self.deadline_service.format_deadline_short(a.deadline_at)
                lines.append(f"• `{a.short_code}`: *{a.course_code}* - {a.title} (Due: {d_str})")
            lines.append("\n_Reply `/approve <ID>` or `/reject <ID>`_")
            return "\n".join(lines)

        elif cmd == "approve":
            if len(parts) < 2:
                return "⚠️ Please specify assignment code or ID. Example: `/approve A1B2`"
            code = parts[1]
            success, msg = await self.review_service.approve_assignment(
                identifier=code,
                admin_jid=sender_jid,
                assignment_repo=assignment_repo,
                notification_repo=notification_repo,
            )
            return msg

        elif cmd == "reject":
            if len(parts) < 2:
                return "⚠️ Please specify assignment code or ID. Example: `/reject A1B2 Not valid`"
            code = parts[1]
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Rejected by admin"
            success, msg = await self.review_service.reject_assignment(
                identifier=code,
                admin_jid=sender_jid,
                assignment_repo=assignment_repo,
                reason=reason,
            )
            return msg

        elif cmd == "edit":
            if len(parts) < 3:
                return "⚠️ Format: `/edit <ID> title=... deadline=YYYY-MM-DD instructions=...`"
            code = parts[1]
            assignment = await assignment_repo.get_by_id_or_short_code(code)
            if not assignment:
                return f"Assignment with ID '{code}' not found."

            raw_args = " ".join(parts[2:])
            updates_made = []

            # Match title=...
            m_title = re.search(r'title=([^=]+?)(?=\s+[a-z]+=|$)', raw_args, re.IGNORECASE)
            if m_title:
                assignment.title = m_title.group(1).strip()
                updates_made.append(f"title -> {assignment.title}")

            # Match course=...
            m_course = re.search(r'course=([^=]+?)(?=\s+[a-z]+=|$)', raw_args, re.IGNORECASE)
            if m_course:
                assignment.course_code = m_course.group(1).strip().upper()
                updates_made.append(f"course -> {assignment.course_code}")

            # Match deadline=...
            m_deadline = re.search(r'deadline=([^=]+?)(?=\s+[a-z]+=|$)', raw_args, re.IGNORECASE)
            if m_deadline:
                d_str = m_deadline.group(1).strip()
                new_dt, clarif = self.deadline_service.parse_deadline(d_str)
                assignment.deadline_at = new_dt
                assignment.deadline_clarification_needed = clarif
                updates_made.append(f"deadline -> {self.deadline_service.format_deadline_for_display(new_dt)}")

                # Cancel and reschedule reminders if already published
                if assignment.status == AssignmentStatus.PUBLISHED:
                    await notification_repo.cancel_for_assignment(assignment.id)
                    if new_dt and not clarif:
                        reminder_time = self.deadline_service.calculate_reminder_time(new_dt)
                        if reminder_time:
                            await notification_repo.create_notification(
                                notification_type="reminder_24h",
                                target_jid=settings.CLASS_GROUP_JID,
                                scheduled_for=reminder_time,
                                assignment_id=assignment.id,
                            )

            await assignment_repo.session.flush()
            await assignment_repo.log_audit(
                assignment_id=assignment.id,
                action="edited",
                actor_jid=sender_jid,
                new_state={"updates": updates_made},
            )

            return f"✏️ Assignment `{assignment.short_code}` updated:\n" + "\n".join(f"• {u}" for u in updates_made)

        elif cmd in ["upcoming", "assignments"]:
            now_utc = datetime.now(timezone.utc)
            upcoming = await assignment_repo.list_active_upcoming(now_utc)
            if not upcoming:
                return "📚 No active upcoming assignments found."

            lines = ["📚 *ACTIVE UPCOMING ASSIGNMENTS:*\n"]
            for a in upcoming:
                d_str = self.deadline_service.format_deadline_short(a.deadline_at)
                lines.append(f"• `{a.short_code}`: *{a.course_code}* – {a.title}\n  Deadline: {d_str}")
            return "\n\n".join(lines)

        return f"❓ Unknown command `/{cmd}`. Type `/help` for available commands."
