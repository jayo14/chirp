from sqlalchemy import Column, String, Boolean
from backend.app.core.database import Base
from backend.app.models.base import UUIDMixin, TimestampMixin


class Administrator(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "administrators"

    phone_or_jid = Column(String(128), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(50), default="admin", nullable=False)
