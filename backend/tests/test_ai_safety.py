import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from backend.app.core.config import settings
from backend.app.core.exceptions import AIExtractionException
from backend.app.integrations.ai.json_utils import parse_clean_json
from backend.app.integrations.ai.gemini import GeminiAIProvider
from backend.app.integrations.ai.openai_compatible import OpenAICompatibleProvider
from backend.app.schemas.webhook import IncomingWhatsAppWebhook
from backend.app.services.orchestrator import WhatsAppOrchestrator
from backend.app.repositories.admin_repo import AdminRepository


def test_parse_clean_json_valid_unfenced():
    raw = '{"course_code": "CSC301", "assignment_title": "Project 1"}'
    parsed = parse_clean_json(raw)
    assert parsed["course_code"] == "CSC301"
    assert parsed["assignment_title"] == "Project 1"


def test_parse_clean_json_with_code_fences():
    raw = '```json\n{"course_code": "MTH202", "confidence": 0.95}\n```'
    parsed = parse_clean_json(raw)
    assert parsed["course_code"] == "MTH202"
    assert parsed["confidence"] == 0.95


def test_parse_clean_json_with_surrounding_commentary():
    raw = 'Here is the extracted assignment info:\n```json\n{"course_code": "PHY101", "confidence": 0.88}\n```\nHope this helps!'
    parsed = parse_clean_json(raw)
    assert parsed["course_code"] == "PHY101"
    assert parsed["confidence"] == 0.88


def test_parse_clean_json_invalid_raises():
    with pytest.raises(ValueError, match="Failed to parse model output as valid JSON"):
        parse_clean_json("This is not JSON at all.")


@pytest.mark.asyncio
async def test_gemini_raises_in_production_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    provider = GeminiAIProvider()

    with pytest.raises(AIExtractionException, match="AI_API_KEY is required in production environment"):
        await provider.extract_assignment("CSC301 Homework due Friday")


@pytest.mark.asyncio
async def test_openai_raises_in_production_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    provider = OpenAICompatibleProvider()

    with pytest.raises(AIExtractionException, match="AI_API_KEY is required in production environment"):
        await provider.extract_assignment("CSC301 Homework due Friday")


@pytest.mark.asyncio
async def test_orchestrator_surfaces_extraction_failure_for_admin_review(test_session):
    admin_repo = AdminRepository(test_session)
    await admin_repo.add_admin("2348000000000@s.whatsapp.net", "Admin User", "SUPERADMIN")
    await test_session.commit()

    failing_extraction_service = AsyncMock()
    failing_extraction_service.extract.side_effect = AIExtractionException("Upstream LLM error: Rate limited")

    gateway_mock = AsyncMock()
    orchestrator = WhatsAppOrchestrator(
        extraction_service=failing_extraction_service,
        gateway_client=gateway_mock,
    )

    payload = IncomingWhatsAppWebhook(
        event="message",
        messageId="fail_msg_101",
        chatJid="123456789-group@g.us",
        senderJid="2348111111111@s.whatsapp.net",
        senderName="Student John",
        isGroup=True,
        isForwarded=False,
        text="Guys, Prof said CSC401 project deadline is extended to next Monday!",
        timestamp=1700000000,
    )

    result = await orchestrator.handle_incoming_message(payload, test_session)

    assert result["status"] == "queued_for_review"
    assert result["course"] == "MANUAL_REVIEW"
    assert gateway_mock.send_text.called
    admin_call_args = gateway_mock.send_text.call_args[1]
    assert "MANUAL_REVIEW" in admin_call_args["text"]
    assert "clarification" in admin_call_args["text"].lower()
