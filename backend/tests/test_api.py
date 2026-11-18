import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "chirp-backend"
        assert "database" in data


@pytest.mark.asyncio
async def test_webhook_unauthorized_without_secret():
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
        # Should fail with 401 or 422 if header missing
        assert response.status_code in [401, 422]


@pytest.mark.asyncio
async def test_webhook_authorized_with_secret():
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


@pytest.mark.asyncio
async def test_list_assignments_api():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/assignments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
