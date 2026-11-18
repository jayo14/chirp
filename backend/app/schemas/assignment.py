from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.assignment import AssignmentStatus


class AssignmentClassification(BaseModel):
    is_assignment_candidate: bool = Field(
        ..., description="True if this message announces or clarifies an assignment"
    )
    classification_type: str = Field(
        ...,
        description="'new_assignment', 'deadline_update', 'clarification', 'cancellation', or 'ordinary_conversation'",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    related_course_code: Optional[str] = None
    reasoning: Optional[str] = None


class ExtractedAssignmentInfo(BaseModel):
    course_code: str = Field(..., description="e.g. CSC 301")
    course_title: Optional[str] = Field(None, description="e.g. Data Structures")
    assignment_title: str = Field(..., description="Short title, e.g. Stack Implementation")
    description: str = Field(..., description="Assignment instructions and overview")
    questions: List[str] = Field(default_factory=list, description="Extracted questions")
    deadline_iso: Optional[str] = Field(
        None, description="ISO format deadline or YYYY-MM-DD / YYYY-MM-DD HH:MM in Africa/Lagos"
    )
    deadline_clarification_needed: bool = Field(
        False, description="True if no definite deadline or needs clarification"
    )
    submission_instructions: Optional[str] = Field(
        None, description="e.g. submit hardcopy to rep, or portal"
    )
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    notes_or_warnings: Optional[str] = None


class AssignmentBase(BaseModel):
    course_code: str
    course_title: Optional[str] = None
    title: str
    description: str
    questions: List[str] = Field(default_factory=list)
    deadline_at: Optional[datetime] = None
    deadline_clarification_needed: bool = False
    submission_instructions: Optional[str] = None


class AssignmentCreate(AssignmentBase):
    status: AssignmentStatus = AssignmentStatus.PENDING_REVIEW


class AssignmentUpdate(BaseModel):
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    questions: Optional[List[str]] = None
    deadline_at: Optional[datetime] = None
    deadline_clarification_needed: Optional[bool] = None
    submission_instructions: Optional[str] = None
    status: Optional[AssignmentStatus] = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_url: str
    mime_type: str
    file_size: Optional[int] = None


class AssignmentOut(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    short_code: str
    status: AssignmentStatus
    published_message_id: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    attachments: List[AttachmentOut] = Field(default_factory=list)
