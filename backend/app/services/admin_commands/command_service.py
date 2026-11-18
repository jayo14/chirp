import re
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from backend.app.core.config import settings
from backend.app.models.assignment import AssignmentStatus
from backend.app.models.notification import NotificationType
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.deadline_management.deadline_service import DeadlineService
from backend.app.services.assignment_publishing.publishing_service import PublishingService

logger = logging.getLogger(__name__)


def parse_edit_fields(args_text: str) -> dict:
    """
    Parses key=value arguments supporting quoted strings ("...", '...') and unquoted tokens.
    Example: title="Assignment 1" deadline=2026-11-20 18:00 desc='Solve problem 1'
    """
    pattern = re.compile(
        r'(?P<key>[a-zA-Z_]+)\s*=\s*(?:"(?P<qval>[^"]*)"|\'(?P<sqval>[^\']*)\'|(?P<rawval>[^=]+?(?=\s+[a-zA-Z_]+\s*=|(?:\s*$))))',
        re.DOTALL
    )
    fields = {}
    for match in pattern.finditer(args_text):
        key = match.group("key").lower()
        val = match.group("qval") if match.group("qval") is not None else (
            match.group("sqval") if match.group("sqval") is not None else match.group("rawval")
        )
        if val is not None:
            fields[key] = val.strip()
    return fields


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
                "• `/cancel <ID> [reason]` - Cancel an assignment and broadcast to class\n"
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

        elif cmd == "cancel":
            if len(parts) < 2:
                return "⚠️ Please specify assignment code or ID. Example: `/cancel A1B2 Lecturer announced cancellation`"
            code = parts[1]
            reason = " ".join(parts[2:]) if len(parts) > 2 else "No submission required."

            assignment = await assignment_repo.get_by_id_or_short_code(code)
            if not assignment:
                return f"Assignment with ID '{code}' not found."

            if assignment.status == AssignmentStatus.CANCELLED:
                return f"⚠️ Assignment {assignment.course_code} ({assignment.short_code}) is already cancelled."

            was_published = assignment.status in [AssignmentStatus.PUBLISHED, AssignmentStatus.UPDATED]

            assignment.status = AssignmentStatus.CANCELLED
            await notification_repo.cancel_for_assignment(assignment.id)
            await assignment_repo.session.flush()

            await assignment_repo.log_audit(
                assignment_id=assignment.id,
                action="cancelled",
                actor_jid=sender_jid,
                new_state={"reason": reason},
            )

            if was_published:
                cancel_text = (
                    f"⚠️ *ASSIGNMENT CANCELLED*\n\n"
                    f"The assignment for *{assignment.course_code}"
                    + (f" – {assignment.course_title}*" if assignment.course_title else "*")
                    + f" ({assignment.title}) has been cancelled.\n"
                    f"No submission is required.\n\n"
                    f"_Reason: {reason}_"
                )
                cancel_notif = await notification_repo.create_notification(
                    notification_type=NotificationType.ASSIGNMENT_UPDATE,
                    target_jid=settings.CLASS_GROUP_JID,
                    scheduled_for=datetime.now(timezone.utc),
                    assignment_id=assignment.id,
                    payload={"text": cancel_text},
                )
                try:
                    await self.review_service.notification_service.execute_notification(
                        notification=cancel_notif,
                        notification_repo=notification_repo,
                        assignment_repo=assignment_repo,
                    )
                except Exception as e:
                    logger.warning(f"Immediate cancellation broadcast deferred: {str(e)}")

                return f"⚠️ Assignment {assignment.course_code} ({assignment.short_code}) has been cancelled and announced to the class group."
            else:
                return f"⚠️ Pending assignment candidate {assignment.course_code} ({assignment.short_code}) cancelled."

        elif cmd == "edit":
            if len(parts) < 3:
                return "⚠️ Format: `/edit <ID> title=... deadline=YYYY-MM-DD course=... instructions=...`"
            code = parts[1]
            assignment = await assignment_repo.get_by_id_or_short_code(code)
            if not assignment:
                return f"Assignment with ID '{code}' not found."

            raw_args = " ".join(parts[2:])
            parsed_fields = parse_edit_fields(raw_args)
            if not parsed_fields:
                return "⚠️ No recognized fields found. Supported: title=, course=, course_title=, deadline=, desc=, instructions="

            updates_made = []

            # 1. Title
            if "title" in parsed_fields:
                assignment.title = parsed_fields["title"]
                updates_made.append(f"title -> {assignment.title}")

            # 2. Course Code
            if "course" in parsed_fields or "course_code" in parsed_fields:
                val = parsed_fields.get("course") or parsed_fields.get("course_code")
                assignment.course_code = val.upper()
                updates_made.append(f"course -> {assignment.course_code}")

            # 3. Course Title
            if "course_title" in parsed_fields:
                assignment.course_title = parsed_fields["course_title"]
                updates_made.append(f"course_title -> {assignment.course_title}")

            # 4. Description
            if "desc" in parsed_fields or "description" in parsed_fields:
                assignment.description = parsed_fields.get("desc") or parsed_fields.get("description")
                updates_made.append("description updated")

            # 5. Instructions
            if "instructions" in parsed_fields or "submission" in parsed_fields:
                assignment.submission_instructions = parsed_fields.get("instructions") or parsed_fields.get("submission")
                updates_made.append("submission instructions updated")

            # 6. Deadline
            deadline_changed = False
            if "deadline" in parsed_fields or "due" in parsed_fields:
                d_str = parsed_fields.get("deadline") or parsed_fields.get("due")
                new_dt, clarif = self.deadline_service.parse_deadline(d_str)
                assignment.deadline_at = new_dt
                assignment.deadline_clarification_needed = clarif
                updates_made.append(f"deadline -> {self.deadline_service.format_deadline_for_display(new_dt)}")
                deadline_changed = True

            if not updates_made:
                return "⚠️ No valid field updates applied."

            # If already published or updated, manage reminders and broadcast update to class group
            if assignment.status in [AssignmentStatus.PUBLISHED, AssignmentStatus.UPDATED]:
                assignment.status = AssignmentStatus.UPDATED

                if deadline_changed:
                    await notification_repo.cancel_for_assignment(assignment.id)
                    if assignment.deadline_at and not assignment.deadline_clarification_needed:
                        reminder_time = self.deadline_service.calculate_reminder_time(assignment.deadline_at)
                        if reminder_time:
                            await notification_repo.create_notification(
                                notification_type=NotificationType.REMINDER_24H,
                                target_jid=settings.CLASS_GROUP_JID,
                                scheduled_for=reminder_time,
                                assignment_id=assignment.id,
                            )

                # Format and dispatch update broadcast to class group via outbox
                reason_str = ", ".join(updates_made)
                update_msg = self.publishing_service.format_update_announcement(
                    assignment=assignment,
                    update_reason=f"Admin modification: {reason_str}",
                )
                update_notif = await notification_repo.create_notification(
                    notification_type=NotificationType.ASSIGNMENT_UPDATE,
                    target_jid=settings.CLASS_GROUP_JID,
                    scheduled_for=datetime.now(timezone.utc),
                    assignment_id=assignment.id,
                    payload={"text": update_msg},
                )
                try:
                    await self.review_service.notification_service.execute_notification(
                        notification=update_notif,
                        notification_repo=notification_repo,
                        assignment_repo=assignment_repo,
                    )
                except Exception as e:
                    logger.warning(f"Immediate dispatch of update broadcast deferred: {str(e)}")

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
