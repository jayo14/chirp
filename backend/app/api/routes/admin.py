from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import verify_admin_auth
from backend.app.models.notification import NotificationType
from backend.app.schemas.assignment import AssignmentOut
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.admin_repo import AdminRepository
from backend.app.repositories.notification_repo import NotificationRepository

from backend.app.services.metrics_service import MetricsService

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_auth)],
)


class AddAdminRequest(BaseModel):
    phone_or_jid: str
    name: Optional[str] = None
    role: str = "admin"


@router.get("/metrics")
async def get_system_metrics(db: AsyncSession = Depends(get_db)):
    """
    Returns metrics tracking PRD success indicators:
    detection counts, delivery reliability, duplicate prevention rate.
    """
    metrics_service = MetricsService(db)
    return await metrics_service.get_metrics_summary()


@router.get("/pending", response_model=List[AssignmentOut])
async def list_pending_assignments(db: AsyncSession = Depends(get_db)):
    repo = AssignmentRepository(db)
    return await repo.list_pending_reviews()


@router.post("/add")
async def add_admin(req: AddAdminRequest, db: AsyncSession = Depends(get_db)):
    repo = AdminRepository(db)
    admin = await repo.add_admin(
        phone_or_jid=req.phone_or_jid,
        name=req.name,
        role=req.role,
    )
    await db.commit()
    return {"success": True, "admin_id": admin.id, "phone_or_jid": admin.phone_or_jid}


@router.post("/trigger-digest")
async def trigger_weekly_digest(db: AsyncSession = Depends(get_db)):
    """
    Manually queues the weekly assignment digest to the class group.
    """
    notif_repo = NotificationRepository(db)
    now_utc = datetime.now(timezone.utc)
    notification = await notif_repo.create_notification(
        notification_type=NotificationType.WEEKLY_DIGEST,
        target_jid=settings.CLASS_GROUP_JID,
        scheduled_for=now_utc,
    )
    await db.commit()
    return {"success": True, "notification_id": notification.id, "scheduled_for": str(now_utc)}
