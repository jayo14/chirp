import enum
from sqlalchemy import Column, String, Text, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class ReviewQueue(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_queue"

    assignment_id = Column(
        String(36),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ReviewStatus, native_enum=False),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by_jid = Column(String(128), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    admin_notes = Column(Text, nullable=True)
    extracted_payload_snapshot = Column(JSON, nullable=True)

    assignment = relationship("Assignment", back_populates="review_records")
