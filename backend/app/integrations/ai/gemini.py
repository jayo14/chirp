import json
import logging
from typing import Optional
import httpx
from backend.app.core.config import settings
from backend.app.schemas.assignment import AssignmentClassification, ExtractedAssignmentInfo
from backend.app.integrations.ai.base import AIProvider
from backend.app.integrations.ai.mock import MockAIProvider

logger = logging.getLogger(__name__)


class GeminiAIProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL or "gemini-1.5-flash"
        self.fallback = MockAIProvider()

    async def classify_message(
        self,
        text: str,
        has_media: bool = False,
    ) -> AssignmentClassification:
        if not self.api_key:
            return await self.fallback.classify_message(text, has_media)

        prompt = f"""
You are an academic assistant for university students.
Classify the following WhatsApp message into one of these categories:
- new_assignment: Announces a new university assignment/homework/term paper/project.
- deadline_update: Extends or changes an existing assignment deadline.
- clarification: Provides clarification or additional questions for an existing assignment.
- cancellation: Cancels an assignment.
- ordinary_conversation: General chatter, greetings, questions between students, banter, etc.

Message text:
\"\"\"{text}\"\"\"

Has media attachment: {has_media}

Return ONLY a valid JSON object matching this schema:
{{
  "is_assignment_candidate": true or false,
  "classification_type": "new_assignment" | "deadline_update" | "clarification" | "cancellation" | "ordinary_conversation",
  "confidence": float between 0.0 and 1.0,
  "related_course_code": "e.g. CSC 301 or null",
  "reasoning": "brief explanation"
}}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                return AssignmentClassification(**parsed)
        except Exception as e:
            logger.warning(f"Gemini API error during classification: {str(e)}. Falling back to heuristics.")
            return await self.fallback.classify_message(text, has_media)

    async def extract_assignment(
        self,
        text: str,
        media_base64: Optional[str] = None,
        mime_type: Optional[str] = None,
        extracted_doc_text: Optional[str] = None,
    ) -> ExtractedAssignmentInfo:
        if not self.api_key:
            return await self.fallback.extract_assignment(
                text, media_base64, mime_type, extracted_doc_text
            )

        prompt = f"""
You are an academic assistant. Extract structured assignment details from the provided message and/or attachment.
All dates/times should be interpreted for university students in Nigeria (timezone Africa/Lagos).

Message text:
\"\"\"{text}\"\"\"

Extracted Document Text (if any):
\"\"\"{extracted_doc_text or ''}\"\"\"

Do NOT invent missing deadlines, course codes or questions.
If deadline is missing or ambiguous, set deadline_clarification_needed to true and deadline_iso to null.

Return ONLY a valid JSON object matching this schema:
{{
  "course_code": "e.g. CSC 301",
  "course_title": "e.g. Data Structures or null",
  "assignment_title": "Short descriptive title",
  "description": "General instructions and scope",
  "questions": ["Question 1...", "Question 2..."],
  "deadline_iso": "YYYY-MM-DD HH:MM or null",
  "deadline_clarification_needed": true or false,
  "submission_instructions": "e.g. submit hardcopy or portal, or null",
  "confidence": 0.95,
  "notes_or_warnings": "any note about readability or missing details"
}}
"""
        parts = []
        if media_base64 and mime_type and mime_type.startswith("image/"):
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": media_base64,
                }
            })
        parts.append({"text": prompt})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                return ExtractedAssignmentInfo(**parsed)
        except Exception as e:
            logger.warning(f"Gemini API error during extraction: {str(e)}. Falling back to heuristics.")
            return await self.fallback.extract_assignment(
                text, media_base64, mime_type, extracted_doc_text
            )
