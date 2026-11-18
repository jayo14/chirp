import logging
from typing import Optional, Tuple
from datetime import datetime
from backend.app.schemas.assignment import ExtractedAssignmentInfo
from backend.app.integrations.ai.base import AIProvider
from backend.app.integrations.ai.factory import get_ai_provider
from backend.app.services.deadline_management.deadline_service import DeadlineService

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        deadline_service: Optional[DeadlineService] = None,
    ):
        self.ai_provider = ai_provider or get_ai_provider()
        self.deadline_service = deadline_service or DeadlineService()

    async def extract(
        self,
        text: str,
        media_base64: Optional[str] = None,
        mime_type: Optional[str] = None,
        extracted_doc_text: Optional[str] = None,
    ) -> Tuple[ExtractedAssignmentInfo, Optional[datetime], bool]:
        """
        Extracts structured assignment info and computes standardized UTC deadline.
        Returns: (extracted_info, parsed_utc_deadline, deadline_clarification_needed)
        """
        extracted = await self.ai_provider.extract_assignment(
            text=text,
            media_base64=media_base64,
            mime_type=mime_type,
            extracted_doc_text=extracted_doc_text,
        )

        # Parse deadline
        deadline_utc, clarification = self.deadline_service.parse_deadline(
            extracted.deadline_iso
        )

        # If AI or deadline service requires clarification
        needs_clarification = (
            extracted.deadline_clarification_needed or clarification or (deadline_utc is None)
        )

        return extracted, deadline_utc, needs_clarification
