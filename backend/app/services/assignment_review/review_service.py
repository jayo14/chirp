import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import update, and_
from backend.app.core.config import settings
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.review import ReviewQueue, ReviewStatus
from backend.app.models.notification import NotificationType
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_publishing.publishing_service import PublishingService
from backend.app.services.notifications.notification_service import NotificationService
from backend.app.services.deadline_management.deadline_service import DeadlineService

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(
        self,
        gateway_client: Optional[WhatsAppGatewayClient] = None,
        publishing_service: Optional[PublishingService] = None,
        deadline_service: Optional[DeadlineService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.gateway_client = gateway_client or WhatsAppGatewayClient()
        self.deadline_service = deadline_service or DeadlineService()
        self.publishing_service = publishing_service or PublishingService(
            gateway_client=self.gateway_client,
            deadline_service=self.deadline_service,
        )
        self.notification_service = notification_service or NotificationService(
            gateway_client=self.gateway_client,
            deadline_service=self.deadline_service,
            publishing_service=self.publishing_service,
        )

    def format_admin_review_notification(self, assignment: Assignment) -> str:
        deadline_str = self.deadline_service.format_deadline_for_display(assignment.deadline_at)
        warning_str = "⚠️ *Warning: Deadline needs clarification!*" if assignment.deadline_clarification_needed else ""

        q_lines = ""
        if assignment.questions:
            q_lines = "\n*Questions:*\n" + "\n".join(f"- {q}" for q in assignment.questions)

        msg = (
            f"🔍 *NEW ASSIGNMENT DETECTED FOR REVIEW*\n\n"
            f"*ID / Code:* `{assignment.short_code}`\n"
            f"*Course:* {assignment.course_code}"
            + (f" – {assignment.course_title}" if assignment.course_title else "")
            + f"\n*Title:* {assignment.title}\n"
            f"*Deadline:* {deadline_str}\n"
            f"{warning_str}\n"
            f"*Description:*\n{assignment.description}\n"
            f"{q_lines}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚙️ *Admin Actions:*\n"
            f"• Approve: `/approve {assignment.short_code}`\n"
            f"• Reject: `/reject {assignment.short_code}`\n"
            f"• Edit: `/edit {assignment.short_code} title=... deadline=YYYY-MM-DD`\n"
        )
        return msg.strip()

    async def notify_admins_for_review(
        self,
        assignment: Assignment,
        admin_repo: AdminRepository,
    ) -> None:
        admin_jids = await admin_repo.get_all_active_admin_jids(settings.admin_jid_list)
        review_text = self.format_admin_review_notification(assignment)

        for admin_jid in admin_jids:
            try:
                await self.gateway_client.send_text(to=admin_jid, text=review_text)
            except Exception as e:
                logger.error(f"Failed to send review prompt to admin {admin_jid}: {str(e)}")

    async def approve_assignment(
        self,
        identifier: str,
        admin_jid: str,
        assignment_repo: AssignmentRepository,
        notification_repo: NotificationRepository,
        notes: Optional[str] = None,
    ) -> Tuple[bool, str]:
        assignment = await assignment_repo.get_by_id_or_short_code(identifier)
        if not assignment:
            return False, f"Assignment with ID/code '{identifier}' not found."

        # 1. Atomic status transition: PENDING_REVIEW -> APPROVED
        # Prevents concurrent double-approvals from creating duplicate publication jobs
        stmt = (
            update(Assignment)
            .where(
                and_(
                    Assignment.id == assignment.id,
                    Assignment.status == AssignmentStatus.PENDING_REVIEW,
                )
            )
            .values(status=AssignmentStatus.APPROVED)
        )
        res = await assignment_repo.session.execute(stmt)
        if res.rowcount == 0:
            cur = await assignment_repo.get_by_id(assignment.id)
            cur_status = cur.status.value if cur else "unknown"
            return False, f"Assignment {assignment.course_code} ({assignment.short_code}) cannot be approved from status '{cur_status}'."

        # 2. Update review record
        for review_rec in assignment.review_records:
            if review_rec.status == ReviewStatus.PENDING:
                review_rec.status = ReviewStatus.APPROVED
                review_rec.reviewed_by_jid = admin_jid
                review_rec.reviewed_at = datetime.now(timezone.utc)
                review_rec.admin_notes = notes

        # 3. Log audit trail
        await assignment_repo.log_audit(
            assignment_id=assignment.id,
            action="approved",
            actor_jid=admin_jid,
            new_state={"notes": notes},
        )

        # 4. Outbox pattern: Persist publication event in the same DB transaction
        now_utc = datetime.now(timezone.utc)
        outbox_event = await notification_repo.create_notification(
            notification_type=NotificationType.ASSIGNMENT_PUBLICATION,
            target_jid=settings.CLASS_GROUP_JID,
            scheduled_for=now_utc,
            assignment_id=assignment.id,
            payload={"admin_jid": admin_jid, "notes": notes},
        )
        await assignment_repo.session.flush()

        # 5. Immediate best-effort decoupled dispatch
        try:
            executed = await self.notification_service.execute_notification(
                notification=outbox_event,
                notification_repo=notification_repo,
                assignment_repo=assignment_repo,
            )
            if executed:
                return True, f"✅ Assignment {assignment.course_code} ({assignment.short_code}) approved and published to class group!"
            else:
                return True, f"✅ Assignment {assignment.course_code} ({assignment.short_code}) approved and queued for publication!"
        except Exception as e:
            logger.warning(f"Immediate publication outbox dispatch deferred: {str(e)}")
            return True, f"✅ Assignment {assignment.course_code} ({assignment.short_code}) approved and queued for publication!"

    async def reject_assignment(
        self,
        identifier: str,
        admin_jid: str,
        assignment_repo: AssignmentRepository,
        reason: Optional[str] = None,
    ) -> Tuple[bool, str]:
        assignment = await assignment_repo.get_by_id_or_short_code(identifier)
        if not assignment:
            return False, f"Assignment with ID/code '{identifier}' not found."

        # Atomic status transition: PENDING_REVIEW -> REJECTED
        stmt = (
            update(Assignment)
            .where(
                and_(
                    Assignment.id == assignment.id,
                    Assignment.status == AssignmentStatus.PENDING_REVIEW,
                )
            )
            .values(status=AssignmentStatus.REJECTED)
        )
        res = await assignment_repo.session.execute(stmt)
        if res.rowcount == 0:
            cur = await assignment_repo.get_by_id(assignment.id)
            cur_status = cur.status.value if cur else "unknown"
            return False, f"Assignment {assignment.course_code} ({assignment.short_code}) cannot be rejected from status '{cur_status}'."

        for review_rec in assignment.review_records:
            if review_rec.status == ReviewStatus.PENDING:
                review_rec.status = ReviewStatus.REJECTED
                review_rec.reviewed_by_jid = admin_jid
                review_rec.reviewed_at = datetime.now(timezone.utc)
                review_rec.admin_notes = reason

        await assignment_repo.log_audit(
            assignment_id=assignment.id,
            action="rejected",
            actor_jid=admin_jid,
            new_state={"reason": reason},
        )

        return True, f"❌ Candidate {assignment.course_code} ({assignment.short_code}) rejected."
