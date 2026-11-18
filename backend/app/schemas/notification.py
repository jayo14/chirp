from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.models.notification import NotificationType, NotificationStatus


class ScheduledNotificationCreate(BaseModel):
    assignment_id: Optional[str] = None
    notification_type: NotificationType
    target_jid: str
    scheduled_for: datetime
    payload: Optional[Dict[str, Any]] = None


class ScheduledNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: Optional[str] = None
    notification_type: NotificationType
    target_jid: str
    scheduled_for: datetime
    status: NotificationStatus
    retry_count: int
    sent_at: Optional[datetime] = None
