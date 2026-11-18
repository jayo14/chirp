from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import verify_admin_auth
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.schemas.assignment import AssignmentOut, AssignmentUpdate
from backend.app.schemas.admin import AdminApprovalRequest, AdminRejectionRequest
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.repositories.notification_repo import NotificationRepository
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.calendar_service import CalendarService
from fastapi.responses import Response

router = APIRouter(prefix="/api/v1/assignments", tags=["Assignments"])


def get_review_service() -> ReviewService:
    return ReviewService()


@router.get("/calendar.ics")
async def get_assignments_calendar_feed(db: AsyncSession = Depends(get_db)):
    """
    Subscribable iCalendar feed (.ics) for Google Calendar, Apple Calendar, Outlook.
    """
    repo = AssignmentRepository(db)
    now_utc = datetime.now(timezone.utc)
    upcoming = await repo.list_active_upcoming(now_utc)
    ics_content = CalendarService.generate_ics(upcoming)
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": 'inline; filename="assignments.ics"'},
    )


@router.get("", response_model=List[AssignmentOut])
async def list_assignments(
    status_filter: Optional[AssignmentStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Assignment)
        .options(
            selectinload(Assignment.attachments),
            selectinload(Assignment.sources),
        )
        .order_by(Assignment.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(Assignment.status == status_filter)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = AssignmentRepository(db)
    assignment = await repo.get_by_id_or_short_code(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found",
        )
    return assignment


@router.post("/{assignment_id}/approve")
async def approve_assignment(
    assignment_id: str,
    body: AdminApprovalRequest = AdminApprovalRequest(),
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(verify_admin_auth),
    review_service: ReviewService = Depends(get_review_service),
):
    repo = AssignmentRepository(db)
    notif_repo = NotificationRepository(db)
    success, message = await review_service.approve_assignment(
        identifier=assignment_id,
        admin_jid="admin_api",
        assignment_repo=repo,
        notification_repo=notif_repo,
        notes=body.notes,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    await db.commit()
    return {"success": True, "message": message}


@router.post("/{assignment_id}/reject")
async def reject_assignment(
    assignment_id: str,
    body: AdminRejectionRequest = AdminRejectionRequest(),
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(verify_admin_auth),
    review_service: ReviewService = Depends(get_review_service),
):
    repo = AssignmentRepository(db)
    success, message = await review_service.reject_assignment(
        identifier=assignment_id,
        admin_jid="admin_api",
        assignment_repo=repo,
        reason=body.reason,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    await db.commit()
    return {"success": True, "message": message}
