import enum
import random
import string
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class AssignmentStatus(str, enum.Enum):
    DETECTED = "detected"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    UPDATED = "updated"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


def generate_short_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=6))


class Assignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assignments"

    short_code = Column(
        String(10),
        unique=True,
        index=True,
        default=generate_short_code,
        nullable=False,
    )
    course_code = Column(String(50), nullable=False, index=True)
    course_title = Column(String(200), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    questions = Column(JSON, nullable=True, default=list)
    deadline_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deadline_clarification_needed = Column(Boolean, default=False, nullable=False)
    submission_instructions = Column(Text, nullable=True)

    status = Column(
        Enum(AssignmentStatus, native_enum=False),
        default=AssignmentStatus.PENDING_REVIEW,
        nullable=False,
        index=True,
    )

    published_message_id = Column(String(100), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sources = relationship("AssignmentSource", back_populates="assignment", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="assignment", cascade="all, delete-orphan")
    review_records = relationship("ReviewQueue", back_populates="assignment", cascade="all, delete-orphan")
    notifications = relationship("ScheduledNotification", back_populates="assignment", cascade="all, delete-orphan")
    audit_logs = relationship("AssignmentAuditLog", back_populates="assignment", cascade="all, delete-orphan")
