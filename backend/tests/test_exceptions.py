import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.exceptions import AssignmentNotFoundException


@pytest.mark.asyncio
async def test_custom_exception_handler():
    @app.get("/test-not-found")
    async def trigger_not_found():
        raise AssignmentNotFoundException("TEST1234")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/test-not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "AssignmentNotFoundException"
        assert "TEST1234" in data["message"]
