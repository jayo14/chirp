import pytest
from backend.app.integrations.ai.mock import MockAIProvider
from backend.app.services.assignment_detection.detection_service import DetectionService
from backend.app.services.assignment_extraction.extraction_service import ExtractionService


@pytest.mark.asyncio
async def test_assignment_classification_new():
    ai = MockAIProvider()
    detector = DetectionService(ai)

    msg = "Good day all, your lecturer gave us an assignment for CSC 301. Submit before Monday."
    result = await detector.detect_assignment_intent(msg, has_media=False)
    assert result.is_assignment_candidate is True
    assert result.classification_type == "new_assignment"
    assert result.related_course_code == "CSC 301"


@pytest.mark.asyncio
async def test_assignment_classification_update():
    ai = MockAIProvider()
    detector = DetectionService(ai)

    msg = "Please note: CSC 301 assignment deadline moved to Wednesday 5pm."
    result = await detector.detect_assignment_intent(msg, has_media=False)
    assert result.is_assignment_candidate is True
    assert result.classification_type == "deadline_update"
    assert result.related_course_code == "CSC 301"


@pytest.mark.asyncio
async def test_assignment_classification_ordinary():
    ai = MockAIProvider()
    detector = DetectionService(ai)

    msg = "Bro who has the lecture slides for yesterday's class? I wasn't around."
    result = await detector.detect_assignment_intent(msg, has_media=False)
    assert result.is_assignment_candidate is False
    assert result.classification_type == "ordinary_conversation"


@pytest.mark.asyncio
async def test_assignment_extraction():
    ai = MockAIProvider()
    extractor = ExtractionService(ai)

    text = """
    CSC 301 Assignment: Stack Implementation
    1. Implement a stack using arrays.
    2. Explain the operations.
    3. Provide time complexities.
    Deadline: 2026-11-23 17:00
    """

    info, deadline_utc, needs_clarif = await extractor.extract(text=text)
    assert info.course_code == "CSC 301"
    assert "Stack Implementation" in info.assignment_title
    assert len(info.questions) == 3
    assert deadline_utc is not None
    assert not needs_clarif
