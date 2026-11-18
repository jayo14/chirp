import pytest
from datetime import datetime, timezone
from backend.app.schemas.webhook import IncomingWhatsAppWebhook
from backend.app.services.orchestrator import WhatsAppOrchestrator
from backend.app.services.assignment_review.review_service import ReviewService
from backend.app.services.assignment_publishing.publishing_service import PublishingService
from backend.app.repositories.assignment_repo import AssignmentRepository
from backend.app.models.assignment import AssignmentStatus


@pytest.mark.asyncio
async def test_incoming_new_assignment_workflow(test_session, mock_gateway_client):
    review_service = ReviewService(gateway_client=mock_gateway_client)
    publishing_service = PublishingService(gateway_client=mock_gateway_client)
    orchestrator = WhatsAppOrchestrator(
        review_service=review_service,
        publishing_service=publishing_service,
        gateway_client=mock_gateway_client,
    )

    webhook_payload = IncomingWhatsAppWebhook(
        messageId="msg_test_101",
        chatJid="120363028392039203@g.us",
        senderJid="2348099999999@s.whatsapp.net",
        senderName="Student John",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="Hello all, lecturer gave us an assignment in CSC 301. Topic: Stack Implementation. Submit before Monday.",
    )

    result = await orchestrator.handle_incoming_message(webhook_payload, test_session)
    assert result["status"] == "queued_for_review"
    assert result["course"] == "CSC 301"

    # Verify review prompt sent to admin
    assert mock_gateway_client.send_text.called

    # Check database state
    assign_repo = AssignmentRepository(test_session)
    assignment = await assign_repo.get_by_id(result["assignment_id"])
    assert assignment is not None
    assert assignment.status == AssignmentStatus.PENDING_REVIEW
    assert assignment.course_code == "CSC 301"


@pytest.mark.asyncio
async def test_duplicate_message_ignored(test_session, mock_gateway_client):
    orchestrator = WhatsAppOrchestrator(gateway_client=mock_gateway_client)

    webhook_payload = IncomingWhatsAppWebhook(
        messageId="msg_test_dup_001",
        chatJid="120363028392039203@g.us",
        senderJid="2348099999999@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="Assignment announcement for CSC 301.",
    )

    # First time -> processed
    first_res = await orchestrator.handle_incoming_message(webhook_payload, test_session)
    assert first_res["status"] == "queued_for_review"

    # Second time -> skipped
    second_res = await orchestrator.handle_incoming_message(webhook_payload, test_session)
    assert second_res["status"] == "skipped"
    assert second_res["reason"] == "already_processed"


@pytest.mark.asyncio
async def test_ordinary_conversation_ignored(test_session, mock_gateway_client):
    orchestrator = WhatsAppOrchestrator(gateway_client=mock_gateway_client)

    webhook_payload = IncomingWhatsAppWebhook(
        messageId="msg_test_chat_002",
        chatJid="120363028392039203@g.us",
        senderJid="2348099999999@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="Guys who is going for tutorial today?",
    )

    result = await orchestrator.handle_incoming_message(webhook_payload, test_session)
    assert result["status"] == "ignored"
    assert result["reason"] == "ordinary_conversation"


@pytest.mark.asyncio
async def test_non_target_group_message_ignored(test_session, mock_gateway_client):
    orchestrator = WhatsAppOrchestrator(gateway_client=mock_gateway_client)

    webhook_payload = IncomingWhatsAppWebhook(
        messageId="msg_unrelated_group_001",
        chatJid="99999999999@g.us",  # Different group from CLASS_GROUP_JID
        senderJid="2348099999999@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="Assignment 2 for CSC 301 is out, submit by Friday!",
    )

    result = await orchestrator.handle_incoming_message(webhook_payload, test_session)
    assert result["status"] == "ignored"
    assert result["reason"] == "unmonitored_group"
    assert not mock_gateway_client.send_text.called
