import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.api.routes.assignments import get_review_service
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository


@pytest.mark.asyncio
async def test_admin_approve_unauthenticated(test_session):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without any header -> 403 Forbidden
        res = await client.post("/api/v1/assignments/some-id/approve", json={})
        assert res.status_code == 403

        # With invalid header -> 403 Forbidden
        res_bad = await client.post(
            "/api/v1/assignments/some-id/approve",
            json={},
            headers={"X-Admin-Api-Key": "wrong-key"},
        )
        assert res_bad.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_approve_authenticated_with_header_and_bearer(test_session, mock_gateway_client):
    repo = AssignmentRepository(test_session)
    assignment = await repo.create_assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Task",
        description="Stack task description",
        deadline_at=datetime.now(timezone.utc),
        status=AssignmentStatus.PENDING_REVIEW,
    )
    assignment2 = await repo.create_assignment(
        course_code="CSC 302",
        course_title="Algorithms",
        title="Queue Task",
        description="Queue task description",
        deadline_at=datetime.now(timezone.utc),
        status=AssignmentStatus.PENDING_REVIEW,
    )
    await test_session.commit()

    async def override_db():
        yield test_session

    mock_review_service = ReviewService(gateway_client=mock_gateway_client)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_review_service] = lambda: mock_review_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test X-Admin-Api-Key header
        res = await client.post(
            f"/api/v1/assignments/{assignment.short_code}/approve",
            json={"notes": "Approved via admin API"},
            headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Test Authorization Bearer header on reject
        res_bearer = await client.post(
            f"/api/v1/assignments/{assignment2.short_code}/reject",
            json={"reason": "Rejected via bearer token"},
            headers={"Authorization": f"Bearer {settings.ADMIN_API_KEY}"},
        )
        assert res_bearer.status_code == 200
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_routes_protected(test_session):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # /api/v1/admin/pending
        assert (await client.get("/api/v1/admin/pending")).status_code == 403
        assert (
            await client.get(
                "/api/v1/admin/pending",
                headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
            )
        ).status_code == 200

        # /api/v1/admin/metrics
        assert (await client.get("/api/v1/admin/metrics")).status_code == 403
        assert (
            await client.get(
                "/api/v1/admin/metrics",
                headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
            )
        ).status_code == 200

        # /api/v1/admin/add
        assert (await client.post("/api/v1/admin/add", json={"phone_or_jid": "2348000"})).status_code == 403
        assert (
            await client.post(
                "/api/v1/admin/add",
                json={"phone_or_jid": "2348000"},
                headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
            )
        ).status_code == 200
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_gateway_webhook_does_not_accept_admin_key(test_session):
    async def override_db():
        yield test_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "messageId": "msg_boundary_001",
            "chatJid": "120363028392039203@g.us",
            "senderJid": "2348000000000@s.whatsapp.net",
            "isGroup": True,
            "timestamp": 1700000000,
            "text": "test",
        }
        # Attempting to call webhook with X-Admin-Api-Key instead of X-Gateway-Secret should fail
        res = await client.post(
            "/api/v1/webhook/whatsapp",
            json=payload,
            headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        )
        assert res.status_code == 401
    app.dependency_overrides.clear()
