import logging
from datetime import datetime, timezone
from typing import List, Optional
from backend.app.core.config import settings
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.review import ReviewQueue, ReviewStatus
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_publishing.publishing_service import PublishingService
from backend.app.services.deadline_management.deadline_service import DeadlineService

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(
        self,
        gateway_client: Optional[WhatsAppGatewayClient] = None,
        publishing_service: Optional[PublishingService] = None,
        deadline_service: Optional[DeadlineService] = None,
    ):
        self.gateway_client = gateway_client or WhatsAppGatewayClient()
        self.deadline_service = deadline_service or DeadlineService()
        self.publishing_service = publishing_service or PublishingService(
            gateway_client=self.gateway_client,
            deadline_service=self.deadline_service,
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

        if assignment.status == AssignmentStatus.PUBLISHED:
            return False, f"Assignment {assignment.course_code} ({assignment.short_code}) is already published."

        assignment.status = AssignmentStatus.APPROVED
        await assignment_repo.session.flush()

        # Update review record
        stmt_review = [r for r in assignment.review_records if r.status == ReviewStatus.PENDING]
        if stmt_review:
            review_rec = stmt_review[0]
            review_rec.status = ReviewStatus.APPROVED
            review_rec.reviewed_by_jid = admin_jid
            review_rec.reviewed_at = datetime.now(timezone.utc)
            review_rec.admin_notes = notes

        await assignment_repo.log_audit(
            assignment_id=assignment.id,
            action="approved",
            actor_jid=admin_jid,
            new_state={"notes": notes},
        )

        # Trigger publishing to group
        await self.publishing_service.publish_assignment(
            assignment=assignment,
            assignment_repo=assignment_repo,
            notification_repo=notification_repo,
        )

        return True, f"✅ Assignment {assignment.course_code} ({assignment.short_code}) approved and published to class group!"

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

        assignment.status = AssignmentStatus.REJECTED
        await assignment_repo.session.flush()

        stmt_review = [r for r in assignment.review_records if r.status == ReviewStatus.PENDING]
        if stmt_review:
            review_rec = stmt_review[0]
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
