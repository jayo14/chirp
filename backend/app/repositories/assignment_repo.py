from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.models.source import AssignmentSource
from backend.app.models.attachment import Attachment
from backend.app.models.review import ReviewQueue, ReviewStatus
from backend.app.models.audit import AssignmentAuditLog


class AssignmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, assignment_id: str) -> Optional[Assignment]:
        stmt = (
            select(Assignment)
            .where(Assignment.id == assignment_id)
            .options(
                selectinload(Assignment.attachments),
                selectinload(Assignment.sources),
                selectinload(Assignment.review_records),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_short_code(self, short_code: str) -> Optional[Assignment]:
        code = short_code.strip().upper()
        stmt = (
            select(Assignment)
            .where(Assignment.short_code == code)
            .options(
                selectinload(Assignment.attachments),
                selectinload(Assignment.sources),
                selectinload(Assignment.review_records),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_short_code(self, identifier: str) -> Optional[Assignment]:
        clean = identifier.strip()
        if len(clean) <= 10:
            found = await self.get_by_short_code(clean)
            if found:
                return found
        return await self.get_by_id(clean)

    async def is_source_processed(self, message_id: str, chat_jid: str) -> bool:
        stmt = select(AssignmentSource.id).where(
            and_(
                AssignmentSource.message_id == message_id,
                AssignmentSource.chat_jid == chat_jid,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_recent_pending_from_sender(
        self,
        sender_jid: str,
        chat_jid: str,
        window_seconds: int = 10,
    ) -> Optional[Assignment]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        stmt = (
            select(Assignment)
            .join(AssignmentSource, Assignment.id == AssignmentSource.assignment_id)
            .where(
                and_(
                    AssignmentSource.sender_jid == sender_jid,
                    AssignmentSource.chat_jid == chat_jid,
                    AssignmentSource.created_at >= cutoff,
                    Assignment.status == AssignmentStatus.PENDING_REVIEW,
                )
            )
            .options(
                selectinload(Assignment.attachments),
                selectinload(Assignment.sources),
                selectinload(Assignment.review_records),
            )
            .order_by(AssignmentSource.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def mark_overdue_assignments(self, now: datetime) -> int:
        """
        Transitions assignments past their deadline from PUBLISHED or UPDATED to OVERDUE.
        Preserves assignment records permanently per PRD section 5.
        """
        stmt = (
            update(Assignment)
            .where(
                and_(
                    Assignment.deadline_at.isnot(None),
                    Assignment.deadline_at <= now,
                    Assignment.status.in_([AssignmentStatus.PUBLISHED, AssignmentStatus.UPDATED]),
                )
            )
            .values(status=AssignmentStatus.OVERDUE)
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount

    async def create_source(
        self,
        message_id: str,
        chat_jid: str,
        sender_jid: str,
        sender_name: Optional[str],
        is_group: bool,
        is_forwarded: bool,
        raw_text: Optional[str],
        raw_caption: Optional[str],
        source_timestamp: Optional[datetime],
        assignment_id: Optional[str] = None,
    ) -> AssignmentSource:
        source = AssignmentSource(
            assignment_id=assignment_id,
            message_id=message_id,
            chat_jid=chat_jid,
            sender_jid=sender_jid,
            sender_name=sender_name,
            is_group=is_group,
            is_forwarded=is_forwarded,
            raw_text=raw_text,
            raw_caption=raw_caption,
            source_timestamp=source_timestamp,
        )
        self.session.add(source)
        await self.session.flush()
        return source

    async def create_assignment(
        self,
        course_code: str,
        course_title: Optional[str],
        title: str,
        description: str,
        questions: Optional[List[str]] = None,
        deadline_at: Optional[datetime] = None,
        deadline_clarification_needed: bool = False,
        submission_instructions: Optional[str] = None,
        status: AssignmentStatus = AssignmentStatus.PENDING_REVIEW,
    ) -> Assignment:
        assignment = Assignment(
            course_code=course_code.upper().strip(),
            course_title=course_title.strip() if course_title else None,
            title=title.strip(),
            description=description.strip(),
            questions=questions or [],
            deadline_at=deadline_at,
            deadline_clarification_needed=deadline_clarification_needed,
            submission_instructions=submission_instructions,
            status=status,
        )
        self.session.add(assignment)
        await self.session.flush()

        # Create review queue entry
        review_entry = ReviewQueue(
            assignment_id=assignment.id,
            status=ReviewStatus.PENDING,
        )
        self.session.add(review_entry)
        await self.session.flush()

        return assignment

    async def add_attachment(
        self,
        assignment_id: Optional[str],
        source_id: Optional[str],
        file_name: str,
        file_url: str,
        storage_path: str,
        mime_type: str,
        file_size: Optional[int] = None,
        extracted_text: Optional[str] = None,
    ) -> Attachment:
        attachment = Attachment(
            assignment_id=assignment_id,
            source_id=source_id,
            file_name=file_name,
            file_url=file_url,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=file_size,
            extracted_text=extracted_text,
        )
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def log_audit(
        self,
        assignment_id: str,
        action: str,
        actor_jid: Optional[str] = None,
        previous_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
    ) -> AssignmentAuditLog:
        log = AssignmentAuditLog(
            assignment_id=assignment_id,
            action=action,
            actor_jid=actor_jid,
            previous_state=previous_state,
            new_state=new_state,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_pending_reviews(self) -> List[Assignment]:
        stmt = (
            select(Assignment)
            .where(Assignment.status == AssignmentStatus.PENDING_REVIEW)
            .options(
                selectinload(Assignment.attachments),
                selectinload(Assignment.sources),
            )
            .order_by(Assignment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_upcoming(self, now: datetime) -> List[Assignment]:
        stmt = (
            select(Assignment)
            .where(
                and_(
                    Assignment.status.in_([AssignmentStatus.APPROVED, AssignmentStatus.PUBLISHED, AssignmentStatus.UPDATED]),
                    or_(
                        Assignment.deadline_at >= now,
                        Assignment.deadline_at.is_(None),
                    ),
                )
            )
            .options(selectinload(Assignment.attachments))
            .order_by(Assignment.deadline_at.asc().nulls_last())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_matching_active_assignment(
        self, course_code: str
    ) -> Optional[Assignment]:
        code = course_code.replace(" ", "").upper()
        stmt = (
            select(Assignment)
            .where(
                and_(
                    Assignment.status.in_([AssignmentStatus.APPROVED, AssignmentStatus.PUBLISHED, AssignmentStatus.UPDATED, AssignmentStatus.PENDING_REVIEW]),
                )
            )
            .order_by(Assignment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        assignments = result.scalars().all()
        for assign in assignments:
            if assign.course_code.replace(" ", "").upper() == code:
                return assign
        return None
