from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class Attachment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "attachments"

    assignment_id = Column(
        String(36),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_id = Column(
        String(36),
        ForeignKey("assignment_sources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)

    assignment = relationship("Assignment", back_populates="attachments")
    source = relationship("AssignmentSource", back_populates="attachments")
