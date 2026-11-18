import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.schemas.webhook import IncomingWhatsAppWebhook
from backend.app.schemas.assignment import AssignmentClassification, ExtractedAssignmentInfo
from backend.app.models.assignment import AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.media_processing.media_service import MediaService
from backend.app.services.assignment_detection.detection_service import DetectionService
from backend.app.services.assignment_extraction.extraction_service import ExtractionService
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.assignment_publishing.publishing_service import PublishingService
from backend.app.services.deadline_management.deadline_service import DeadlineService
from backend.app.services.admin_commands.command_service import AdminCommandService
from backend.app.services.student_commands.student_command_service import StudentCommandService
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient

logger = logging.getLogger(__name__)


class WhatsAppOrchestrator:
    def __init__(
        self,
        media_service: Optional[MediaService] = None,
        detection_service: Optional[DetectionService] = None,
        extraction_service: Optional[ExtractionService] = None,
        review_service: Optional[ReviewService] = None,
        publishing_service: Optional[PublishingService] = None,
        deadline_service: Optional[DeadlineService] = None,
        admin_command_service: Optional[AdminCommandService] = None,
        student_command_service: Optional[StudentCommandService] = None,
        gateway_client: Optional[WhatsAppGatewayClient] = None,
    ):
        self.gateway_client = gateway_client or WhatsAppGatewayClient()
        self.deadline_service = deadline_service or DeadlineService()
        self.media_service = media_service or MediaService()
        self.detection_service = detection_service or DetectionService()
        self.extraction_service = extraction_service or ExtractionService(
            deadline_service=self.deadline_service
        )
        self.publishing_service = publishing_service or PublishingService(
            gateway_client=self.gateway_client,
            deadline_service=self.deadline_service,
        )
        self.review_service = review_service or ReviewService(
            gateway_client=self.gateway_client,
            publishing_service=self.publishing_service,
            deadline_service=self.deadline_service,
        )
        self.admin_command_service = admin_command_service or AdminCommandService(
            review_service=self.review_service,
            deadline_service=self.deadline_service,
        )
        self.student_command_service = student_command_service or StudentCommandService(
            deadline_service=self.deadline_service
        )

    async def handle_incoming_message(
        self,
        payload: IncomingWhatsAppWebhook,
        session: AsyncSession,
    ) -> dict:
        assignment_repo = AssignmentRepository(session)
        admin_repo = AdminRepository(session)
        notification_repo = NotificationRepository(session)

        # 1. Duplicate check
        if await assignment_repo.is_source_processed(payload.messageId, payload.chatJid):
            logger.info(f"Message {payload.messageId} already processed. Skipping.")
            return {"status": "skipped", "reason": "already_processed"}

        # 2. Restrict group processing strictly to CLASS_GROUP_JID
        if payload.isGroup and settings.CLASS_GROUP_JID and payload.chatJid != settings.CLASS_GROUP_JID:
            logger.info(
                f"Ignoring message {payload.messageId} from non-target group {payload.chatJid} "
                f"(configured target: {settings.CLASS_GROUP_JID})"
            )
            return {"status": "ignored", "reason": "unmonitored_group"}

        # 2. Convert timestamp
        source_ts = datetime.fromtimestamp(payload.timestamp, tz=timezone.utc)

        # 3. Handle Admin commands and Student queries in private chat
        text_content = payload.full_text
        if not payload.isGroup:
            is_admin = await admin_repo.is_admin(payload.senderJid, settings.admin_jid_list)
            if is_admin and self.admin_command_service.is_command(text_content):
                reply_text = await self.admin_command_service.handle_command(
                    sender_jid=payload.senderJid,
                    text=text_content,
                    assignment_repo=assignment_repo,
                    admin_repo=admin_repo,
                    notification_repo=notification_repo,
                )
                await self.gateway_client.send_text(
                    to=payload.senderJid,
                    text=reply_text,
                    quoted_message_id=payload.messageId,
                )
                await assignment_repo.create_source(
                    message_id=payload.messageId,
                    chat_jid=payload.chatJid,
                    sender_jid=payload.senderJid,
                    sender_name=payload.senderName,
                    is_group=payload.isGroup,
                    is_forwarded=payload.isForwarded,
                    raw_text=payload.text,
                    raw_caption=payload.caption,
                    source_timestamp=source_ts,
                )
                await session.commit()
                return {"status": "command_handled"}

            elif not is_admin and not payload.media and self.student_command_service.is_student_query(text_content):
                student_reply = await self.student_command_service.handle_query(
                    sender_jid=payload.senderJid,
                    text=text_content,
                    assignment_repo=assignment_repo,
                )
                await self.gateway_client.send_text(
                    to=payload.senderJid,
                    text=student_reply,
                    quoted_message_id=payload.messageId,
                )
                await session.commit()
                return {"status": "student_query_answered"}

        # 4. Process Media if present
        saved_file_url = None
        saved_storage_path = None
        extracted_doc_text = None
        media_result = None

        if payload.media:
            try:
                media_result = await self.media_service.process_incoming_media(payload.media)
                saved_file_url = media_result.file_url
                saved_storage_path = media_result.storage_path
                extracted_doc_text = media_result.extracted_text
            except Exception as e:
                logger.error(f"Error processing media for message {payload.messageId}: {str(e)}")

        # 5. Detect Assignment Intent
        try:
            classification = await self.detection_service.detect_assignment_intent(
                text=text_content,
                has_media=bool(payload.media),
            )
        except Exception as e:
            logger.error(f"Classification failed for message {payload.messageId}: {str(e)}")
            lower_text = text_content.lower() if text_content else ""
            keywords = ["assignment", "homework", "due date", "submission", "deadline", "submit", "project"]
            is_candidate = bool(payload.media) or any(k in lower_text for k in keywords)
            classification = AssignmentClassification(
                is_assignment_candidate=is_candidate,
                classification_type="new_assignment" if is_candidate else "ordinary_conversation",
                confidence=0.0,
                reasoning=f"AI classification failed; heuristic fallback applied: {str(e)}",
            )

        logger.info(
            f"Classification for message {payload.messageId}: type={classification.classification_type}, "
            f"confidence={classification.confidence}, candidate={classification.is_assignment_candidate}"
        )

        if not classification.is_assignment_candidate:
            # Ordinary conversation -> ignore
            await session.commit()
            return {"status": "ignored", "reason": "ordinary_conversation"}

        # 6. Check if it's an update / cancellation to an existing assignment
        if classification.classification_type in ["deadline_update", "cancellation", "clarification"]:
            matched_assignment = None
            if classification.related_course_code:
                matched_assignment = await assignment_repo.find_matching_active_assignment(
                    classification.related_course_code
                )

            if matched_assignment:
                if classification.classification_type == "deadline_update":
                    new_dt, clarif = self.deadline_service.parse_deadline(text_content)
                    if new_dt:
                        matched_assignment.deadline_at = new_dt
                        matched_assignment.deadline_clarification_needed = clarif
                        matched_assignment.status = AssignmentStatus.UPDATED
                        await session.flush()

                        # Reschedule reminders
                        await notification_repo.cancel_for_assignment(matched_assignment.id)
                        reminder_time = self.deadline_service.calculate_reminder_time(new_dt)
                        if reminder_time:
                            await notification_repo.create_notification(
                                notification_type="reminder_24h",
                                target_jid=settings.CLASS_GROUP_JID,
                                scheduled_for=reminder_time,
                                assignment_id=matched_assignment.id,
                            )

                        # Announce update to group
                        update_msg = self.publishing_service.format_update_announcement(
                            matched_assignment,
                            f"Deadline extended/modified to: {self.deadline_service.format_deadline_for_display(new_dt)}"
                        )
                        await self.gateway_client.send_text(
                            to=settings.CLASS_GROUP_JID,
                            text=update_msg,
                        )

                        await assignment_repo.log_audit(
                            assignment_id=matched_assignment.id,
                            action="deadline_update",
                            actor_jid=payload.senderJid,
                            new_state={"new_deadline": str(new_dt)},
                        )

                elif classification.classification_type == "cancellation":
                    matched_assignment.status = AssignmentStatus.CANCELLED
                    await notification_repo.cancel_for_assignment(matched_assignment.id)
                    cancel_msg = (
                        f"⚠️ *ASSIGNMENT CANCELLED*\n\n"
                        f"The assignment for *{matched_assignment.course_code} - {matched_assignment.title}* "
                        f"has been cancelled.\nNo submission is required."
                    )
                    await self.gateway_client.send_text(
                        to=settings.CLASS_GROUP_JID,
                        text=cancel_msg,
                    )
                    await assignment_repo.log_audit(
                        assignment_id=matched_assignment.id,
                        action="cancelled",
                        actor_jid=payload.senderJid,
                    )

                # Record source
                await assignment_repo.create_source(
                    message_id=payload.messageId,
                    chat_jid=payload.chatJid,
                    sender_jid=payload.senderJid,
                    sender_name=payload.senderName,
                    is_group=payload.isGroup,
                    is_forwarded=payload.isForwarded,
                    raw_text=payload.text,
                    raw_caption=payload.caption,
                    source_timestamp=source_ts,
                    assignment_id=matched_assignment.id,
                )
                await session.commit()
                return {"status": "updated_existing_assignment", "assignment_id": matched_assignment.id}

        # 7. New Assignment Flow
        media_b64 = payload.media.dataBase64 if payload.media else None
        mime = payload.media.mimeType if payload.media else None

        # For scanned PDFs where digital text is absent, supply rendered page images for vision models
        if media_result and media_result.is_scanned and media_result.rendered_images:
            media_b64 = media_result.rendered_images[0]
            mime = "image/jpeg"

        try:
            extracted_info, deadline_utc, needs_clarif = await self.extraction_service.extract(
                text=text_content,
                media_base64=media_b64,
                mime_type=mime,
                extracted_doc_text=extracted_doc_text,
            )
        except Exception as e:
            logger.error(f"Extraction failed for message {payload.messageId}: {str(e)}. Surfacing for manual admin review.")
            extracted_info = ExtractedAssignmentInfo(
                course_code="MANUAL_REVIEW",
                course_title="AI Extraction Error",
                assignment_title=f"Unparsed Assignment from {payload.senderName or payload.senderJid}",
                description=f"Automated AI extraction failed ({type(e).__name__}: {str(e)}).\n\nOriginal Text:\n{text_content}",
                questions=[],
                submission_instructions="Please edit or verify this assignment manually via /edit or the admin panel.",
                deadline_iso=None,
                deadline_clarification_needed=True,
                confidence=0.0,
            )
            deadline_utc = None
            needs_clarif = True

        assignment = await assignment_repo.create_assignment(
            course_code=extracted_info.course_code,
            course_title=extracted_info.course_title,
            title=extracted_info.assignment_title,
            description=extracted_info.description,
            questions=extracted_info.questions,
            deadline_at=deadline_utc,
            deadline_clarification_needed=needs_clarif,
            submission_instructions=extracted_info.submission_instructions,
            status=AssignmentStatus.PENDING_REVIEW,
        )

        # Record source
        source_record = await assignment_repo.create_source(
            message_id=payload.messageId,
            chat_jid=payload.chatJid,
            sender_jid=payload.senderJid,
            sender_name=payload.senderName,
            is_group=payload.isGroup,
            is_forwarded=payload.isForwarded,
            raw_text=payload.text,
            raw_caption=payload.caption,
            source_timestamp=source_ts,
            assignment_id=assignment.id,
        )

        # Record attachment if any
        if payload.media and saved_file_url and saved_storage_path:
            await assignment_repo.add_attachment(
                assignment_id=assignment.id,
                source_id=source_record.id,
                file_name=payload.media.fileName or "attachment",
                file_url=saved_file_url,
                storage_path=saved_storage_path,
                mime_type=payload.media.mimeType,
                file_size=payload.media.fileSize,
                extracted_text=extracted_doc_text,
            )

        await assignment_repo.log_audit(
            assignment_id=assignment.id,
            action="detected",
            actor_jid=payload.senderJid,
            new_state={"confidence": extracted_info.confidence},
        )

        await session.commit()

        # Send private review notification to administrators
        await self.review_service.notify_admins_for_review(
            assignment=assignment,
            admin_repo=admin_repo,
        )

        return {
            "status": "queued_for_review",
            "assignment_id": assignment.id,
            "short_code": assignment.short_code,
            "course": assignment.course_code,
        }
