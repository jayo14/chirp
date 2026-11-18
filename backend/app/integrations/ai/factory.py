from backend.app.core.config import settings
from backend.app.integrations.ai.base import AIProvider
from backend.app.integrations.ai.mock import MockAIProvider
from backend.app.integrations.ai.gemini import GeminiAIProvider
from backend.app.integrations.ai.openai_compatible import OpenAICompatibleProvider


def get_ai_provider() -> AIProvider:
    provider = settings.AI_PROVIDER.lower().strip()
    if provider == "gemini":
        return GeminiAIProvider()
    elif provider in ("openai", "gpt"):
        return OpenAICompatibleProvider()
    return MockAIProvider()
