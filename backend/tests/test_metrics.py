import pytest
from datetime import datetime, timezone
from backend.app.models.assignment import Assignment, AssignmentStatus
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.services.metrics_service import MetricsService


@pytest.mark.asyncio
async def test_metrics_calculation(test_session):
    repo = AssignmentRepository(test_session)

    # Create published assignment
    await repo.create_assignment(
        course_code="CSC 301",
        course_title="Data Structures",
        title="Stack Assignment",
        description="Stack implementation",
        status=AssignmentStatus.PUBLISHED,
    )
    # Create rejected assignment
    await repo.create_assignment(
        course_code="CSC 309",
        course_title="AI",
        title="Draft",
        description="Draft",
        status=AssignmentStatus.REJECTED,
    )
    await test_session.commit()

    metrics_service = MetricsService(test_session)
    summary = await metrics_service.get_metrics_summary()

    assert summary["assignments"]["total_detected"] >= 2
    assert summary["assignments"]["published"] >= 1
    assert summary["assignments"]["rejected"] >= 1
    assert summary["delivery_reliability"]["duplicate_publications"] == 0
