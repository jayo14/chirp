import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Enum,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class NotificationType(str, enum.Enum):
    REMINDER_24H = "reminder_24h"
    WEEKLY_DIGEST = "weekly_digest"
    ADMIN_REVIEW = "admin_review"
    ASSIGNMENT_UPDATE = "assignment_update"
    ASSIGNMENT_PUBLICATION = "assignment_publication"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledNotification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scheduled_notifications"

    assignment_id = Column(
        String(36),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    notification_type = Column(
        Enum(NotificationType, native_enum=False),
        nullable=False,
        index=True,
    )
    target_jid = Column(String(128), nullable=False)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(
        Enum(NotificationStatus, native_enum=False),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    last_error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=True)

    assignment = relationship("Assignment", back_populates="notifications")
