from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class AssignmentAuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assignment_audit_logs"

    assignment_id = Column(
        String(36),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(100), nullable=False)
    actor_jid = Column(String(128), nullable=True)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)

    assignment = relationship("Assignment", back_populates="audit_logs")
