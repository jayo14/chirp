from abc import ABC, abstractmethod
from typing import Optional
from backend.app.schemas.assignment import AssignmentClassification, ExtractedAssignmentInfo


class AIProvider(ABC):
    @abstractmethod
    async def classify_message(
        self,
        text: str,
        has_media: bool = False,
    ) -> AssignmentClassification:
        """
        Classifies incoming WhatsApp message into:
        'new_assignment', 'deadline_update', 'clarification', 'cancellation', or 'ordinary_conversation'.
        """
        pass

    @abstractmethod
    async def extract_assignment(
        self,
        text: str,
        media_base64: Optional[str] = None,
        mime_type: Optional[str] = None,
        extracted_doc_text: Optional[str] = None,
    ) -> ExtractedAssignmentInfo:
        """
        Extracts structured assignment information (course_code, title, description, questions, deadline, submission instructions).
        """
        pass
