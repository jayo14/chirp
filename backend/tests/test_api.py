import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_db


@pytest.mark.asyncio
async def test_health_endpoint(test_session):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "chirp-backend"
        assert "database" in data
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_webhook_unauthorized_without_secret(test_session):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "messageId": "msg_unauth_001",
            "chatJid": "120363028392039203@g.us",
            "senderJid": "2348000000000@s.whatsapp.net",
            "isGroup": True,
            "isForwarded": False,
            "timestamp": 1700000000,
            "text": "test",
        }
        response = await client.post("/api/v1/webhook/whatsapp", json=payload)
        assert response.status_code in [401, 422]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_webhook_authorized_with_secret(test_session, mock_gateway_client):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "messageId": "msg_auth_002",
            "chatJid": "120363028392039203@g.us",
            "senderJid": "2348000000000@s.whatsapp.net",
            "isGroup": True,
            "isForwarded": False,
            "timestamp": 1700000000,
            "text": "Assignment: CSC 301 stack project. Submit tomorrow.",
        }
        headers = {"X-Gateway-Secret": settings.WHATSAPP_GATEWAY_SECRET}
        response = await client.post("/api/v1/webhook/whatsapp", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["success"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_assignments_api(test_session):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/assignments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    app.dependency_overrides.clear()
