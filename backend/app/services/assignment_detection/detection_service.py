import logging
from typing import Optional
from backend.app.schemas.assignment import AssignmentClassification
from backend.app.integrations.ai.base import AIProvider
from backend.app.integrations.ai.factory import get_ai_provider

logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider or get_ai_provider()

    async def detect_assignment_intent(
        self,
        text: str,
        has_media: bool = False,
    ) -> AssignmentClassification:
        """
        Determines whether an incoming message is an assignment announcement,
        an update to an existing assignment, or an ordinary discussion.
        """
        if not text and not has_media:
            return AssignmentClassification(
                is_assignment_candidate=False,
                classification_type="ordinary_conversation",
                confidence=1.0,
                reasoning="Empty message without text or media",
            )

        return await self.ai_provider.classify_message(text=text, has_media=has_media)
