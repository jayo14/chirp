from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class AssignmentSource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assignment_sources"

    assignment_id = Column(
        String(36),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    message_id = Column(String(128), nullable=False, index=True)
    chat_jid = Column(String(128), nullable=False, index=True)
    sender_jid = Column(String(128), nullable=False)
    sender_name = Column(String(255), nullable=True)
    is_group = Column(Boolean, default=True, nullable=False)
    is_forwarded = Column(Boolean, default=False, nullable=False)
    raw_text = Column(Text, nullable=True)
    raw_caption = Column(Text, nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("message_id", "chat_jid", name="uq_source_message_chat"),
    )

    assignment = relationship("Assignment", back_populates="sources")
    attachments = relationship("Attachment", back_populates="source", cascade="all, delete-orphan")
