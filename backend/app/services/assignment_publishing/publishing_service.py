import base64
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from backend.app.core.config import settings
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.attachment import Attachment
from backend.app.models.notification import NotificationType
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient
from backend.app.integrations.storage.base import StorageProvider
from backend.app.integrations.storage.factory import get_storage_provider
from backend.app.services.deadline_management.deadline_service import DeadlineService
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.notification_repo import NotificationRepository

logger = logging.getLogger(__name__)

MAX_MEDIA_BYTES = 25 * 1024 * 1024  # 25 MB max media size


class PublishingService:
    def __init__(
        self,
        gateway_client: Optional[WhatsAppGatewayClient] = None,
        deadline_service: Optional[DeadlineService] = None,
        storage_provider: Optional[StorageProvider] = None,
    ):
        self.gateway_client = gateway_client or WhatsAppGatewayClient()
        self.deadline_service = deadline_service or DeadlineService()
        self.storage_provider = storage_provider or get_storage_provider()

    async def _resolve_media_payload(self, attachment: Attachment) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolves media content for gateway dispatch.
        Returns: (file_url, media_base64)
        Raises ValueError if local file is missing, empty, or exceeds payload limit.
        """
        # If public remote URL (e.g. Supabase Storage public URL)
        if attachment.file_url and attachment.file_url.startswith(("http://", "https://")):
            return attachment.file_url, None

        # Local storage: read file bytes and encode to Base64
        file_bytes = await self.storage_provider.read_file(attachment.storage_path)
        if not file_bytes:
            raise ValueError(
                f"Cannot publish attachment '{attachment.file_name}': file content not found at '{attachment.storage_path}'"
            )

        if len(file_bytes) > MAX_MEDIA_BYTES:
            raise ValueError(
                f"Attachment '{attachment.file_name}' exceeds maximum WhatsApp payload size "
                f"({len(file_bytes)} bytes > {MAX_MEDIA_BYTES} bytes)"
            )

        media_base64 = base64.b64encode(file_bytes).decode("ascii")
        return None, media_base64

    def format_announcement(self, assignment: Assignment) -> str:
        course_line = f"{assignment.course_code}"
        if assignment.course_title:
            course_line += f" – {assignment.course_title}"

        deadline_str = self.deadline_service.format_deadline_for_display(assignment.deadline_at)

        # Format questions/instructions
        instructions_content = assignment.description.strip()
        if assignment.questions and len(assignment.questions) > 0:
            formatted_q = []
            for idx, q in enumerate(assignment.questions):
                clean_q = q.strip()
                if not any(clean_q.startswith(prefix) for prefix in [f"{idx+1}.", f"{idx+1})", "-", "*"]):
                    clean_q = f"{idx + 1}. {clean_q}"
                formatted_q.append(clean_q)
            instructions_content += "\n\n" + "\n".join(formatted_q)

        submission = assignment.submission_instructions or "As specified by your lecturer."

        attachment_note = ""
        if assignment.attachments and len(assignment.attachments) > 0:
            attachment_note = "\n📎 *Original Assignment:* Attached.\n"

        reminder_note = "⏰ A reminder will be sent before the submission deadline."
        if not assignment.deadline_at or assignment.deadline_clarification_needed:
            reminder_note = "⏰ Reminder will be scheduled once the deadline is confirmed."

        message = (
            f"📚 *NEW ASSIGNMENT*\n\n"
            f"*Course:* {course_line}\n\n"
            f"*Assignment:* {assignment.title}\n\n"
            f"*Instructions:*\n{instructions_content}\n\n"
            f"*Submission Deadline:* {deadline_str}\n\n"
            f"*Submission Instructions:* {submission}\n"
            f"{attachment_note}\n"
            f"{reminder_note}\n\n"
            f"Please start early!"
        )
        return message.strip()

    def format_update_announcement(self, assignment: Assignment, update_reason: str) -> str:
        course_line = f"{assignment.course_code}"
        if assignment.course_title:
            course_line += f" – {assignment.course_title}"

        deadline_str = self.deadline_service.format_deadline_for_display(assignment.deadline_at)

        message = (
            f"📢 *ASSIGNMENT UPDATE*\n\n"
            f"*Course:* {course_line}\n"
            f"*Assignment:* {assignment.title}\n"
            f"*Update:* {update_reason}\n\n"
            f"*Current Deadline:* {deadline_str}\n\n"
            f"Please take note of the change!"
        )
        return message.strip()

    async def publish_assignment(
        self,
        assignment: Assignment,
        assignment_repo: AssignmentRepository,
        notification_repo: NotificationRepository,
        target_group_jid: Optional[str] = None,
    ) -> bool:
        group_jid = target_group_jid or settings.CLASS_GROUP_JID
        message_text = self.format_announcement(assignment)

        published_msg_id = None

        # Check if there are attachments to send
        if assignment.attachments and len(assignment.attachments) > 0:
            # Send primary attachment with caption
            primary_att = assignment.attachments[0]
            media_type = "document" if "pdf" in primary_att.mime_type.lower() else "image"
            file_url, media_base64 = await self._resolve_media_payload(primary_att)

            res = await self.gateway_client.send_media(
                to=group_jid,
                media_type=media_type,
                file_url=file_url,
                media_base64=media_base64,
                file_name=primary_att.file_name,
                caption=message_text,
            )
            if not res.get("success"):
                raise RuntimeError(f"Gateway failed to send primary attachment: {res.get('error')}")
            published_msg_id = res.get("messageId")

            # Send any subsequent attachments
            for extra_att in assignment.attachments[1:]:
                extra_type = "document" if "pdf" in extra_att.mime_type.lower() else "image"
                extra_url, extra_b64 = await self._resolve_media_payload(extra_att)
                sub_res = await self.gateway_client.send_media(
                    to=group_jid,
                    media_type=extra_type,
                    file_url=extra_url,
                    media_base64=extra_b64,
                    file_name=extra_att.file_name,
                    caption=f"📎 Additional attachment for {assignment.course_code} - {assignment.title}",
                )
                if not sub_res.get("success"):
                    logger.warning(f"Gateway failed to send subsequent attachment {extra_att.file_name}: {sub_res.get('error')}")
        else:
            # Send text only
            res = await self.gateway_client.send_text(
                to=group_jid,
                text=message_text,
            )
            if not res.get("success"):
                raise RuntimeError(f"Gateway failed to send announcement: {res.get('error')}")
            published_msg_id = res.get("messageId")

        # Update assignment state
        assignment.status = AssignmentStatus.PUBLISHED
        assignment.published_message_id = published_msg_id
        assignment.published_at = datetime.now(timezone.utc)
        await assignment_repo.session.flush()

        await assignment_repo.log_audit(
            assignment_id=assignment.id,
            action="published",
            new_state={"published_message_id": published_msg_id, "group": group_jid},
        )

        # Schedule 24h reminder if valid deadline exists
        if assignment.deadline_at and not assignment.deadline_clarification_needed:
            reminder_time = self.deadline_service.calculate_reminder_time(assignment.deadline_at)
            if reminder_time:
                await notification_repo.create_notification(
                    notification_type=NotificationType.REMINDER_24H,
                    target_jid=group_jid,
                    scheduled_for=reminder_time,
                    assignment_id=assignment.id,
                )

        return True
