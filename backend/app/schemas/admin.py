from typing import Optional, Dict, Any
from pydantic import BaseModel


class AdminApprovalRequest(BaseModel):
    notes: Optional[str] = None


class AdminRejectionRequest(BaseModel):
    reason: Optional[str] = None


class AdminEditRequest(BaseModel):
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    deadline_iso: Optional[str] = None
    submission_instructions: Optional[str] = None


class AdminCommand(BaseModel):
    command: str  # e.g. "pending", "approve", "reject", "edit", "assignments", "upcoming", "help"
    target_id_or_code: Optional[str] = None
    args: Dict[str, Any] = {}
