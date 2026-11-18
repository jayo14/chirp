import logging
from typing import Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.exceptions import AIExtractionException
from backend.app.schemas.assignment import AssignmentClassification, ExtractedAssignmentInfo
from backend.app.integrations.ai.base import AIProvider
from backend.app.integrations.ai.mock import MockAIProvider
from backend.app.integrations.ai.json_utils import parse_clean_json

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL or "gpt-4o-mini"
        self.fallback = MockAIProvider()

    async def classify_message(
        self,
        text: str,
        has_media: bool = False,
    ) -> AssignmentClassification:
        if not self.api_key:
            if settings.APP_ENV in ["production", "staging"]:
                raise AIExtractionException("AI_API_KEY is required in production environment.")
            return await self.fallback.classify_message(text, has_media)

        prompt = f"""
Classify this WhatsApp message:
Message: \"\"\"{text}\"\"\"
Has Media: {has_media}

Return ONLY a JSON object:
{{
  "is_assignment_candidate": true or false,
  "classification_type": "new_assignment" | "deadline_update" | "clarification" | "cancellation" | "ordinary_conversation",
  "confidence": 0.95,
  "related_course_code": "e.g. CSC 301 or null",
  "reasoning": "brief explanation"
}}
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = parse_clean_json(content)
                return AssignmentClassification(**parsed)
        except Exception as e:
            logger.error(f"OpenAI classification error: {str(e)}")
            if settings.APP_ENV in ["production", "staging"] or settings.AI_PROVIDER != "mock":
                raise AIExtractionException(f"OpenAI classification failed: {str(e)}") from e
            return await self.fallback.classify_message(text, has_media)

    async def extract_assignment(
        self,
        text: str,
        media_base64: Optional[str] = None,
        mime_type: Optional[str] = None,
        extracted_doc_text: Optional[str] = None,
    ) -> ExtractedAssignmentInfo:
        if not self.api_key:
            if settings.APP_ENV in ["production", "staging"]:
                raise AIExtractionException("AI_API_KEY is required in production environment.")
            return await self.fallback.extract_assignment(
                text, media_base64, mime_type, extracted_doc_text
            )

        content_parts = []
        content_parts.append({
            "type": "text",
            "text": f"Extract assignment details in Africa/Lagos timezone.\nText: {text}\nDocument: {extracted_doc_text or ''}\nOutput JSON schema with fields: course_code, course_title, assignment_title, description, questions, deadline_iso, deadline_clarification_needed, submission_instructions, confidence, notes_or_warnings."
        })

        if media_base64 and mime_type and mime_type.startswith("image/"):
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{media_base64}"}
            })

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_parts}],
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = parse_clean_json(content)
                return ExtractedAssignmentInfo(**parsed)
        except Exception as e:
            logger.error(f"OpenAI extraction error: {str(e)}")
            if settings.APP_ENV in ["production", "staging"] or settings.AI_PROVIDER != "mock":
                raise AIExtractionException(f"OpenAI extraction failed: {str(e)}") from e
            return await self.fallback.extract_assignment(
                text, media_base64, mime_type, extracted_doc_text
            )
