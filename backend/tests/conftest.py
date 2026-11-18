import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.app.models import Base
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient
from unittest.mock import AsyncMock


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_gateway_client():
    client = WhatsAppGatewayClient(base_url="http://mock-gateway:3000", secret="test-secret")
    client.send_text = AsyncMock(return_value={"success": True, "messageId": "msg_mock_text_123"})
    client.send_media = AsyncMock(return_value={"success": True, "messageId": "msg_mock_media_456"})
    client.get_status = AsyncMock(return_value={"status": "connected", "connectedPhone": "2348000000000"})
    return client
