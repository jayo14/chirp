import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from backend.app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UUIDMixin:
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
