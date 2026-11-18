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


@pytest.mark.asyncio
async def test_multi_image_media_grouping(test_session, mock_gateway_client):
    import base64
    from backend.app.schemas.webhook import IncomingMediaInfo
    from backend.app.core.config import settings

    orchestrator = WhatsAppOrchestrator(gateway_client=mock_gateway_client)
    sample_b64 = base64.b64encode(b"fake image bytes page 1").decode("ascii")

    # 1. First image with assignment caption
    msg1 = IncomingWhatsAppWebhook(
        messageId="msg_album_001",
        chatJid=settings.CLASS_GROUP_JID,
        senderJid="2348011112222@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="Assignment in CSC 301 on Graph Algorithms. Page 1 attached.",
        media=IncomingMediaInfo(
            mimeType="image/jpeg",
            fileName="page1.jpg",
            fileSize=len(sample_b64),
            dataBase64=sample_b64,
        ),
    )

    res1 = await orchestrator.handle_incoming_message(msg1, test_session)
    assert res1["status"] == "queued_for_review"
    assign_id = res1["assignment_id"]

    # 2. Second image sent 1 second later with no caption (continuation page)
    sample2_b64 = base64.b64encode(b"fake image bytes page 2").decode("ascii")
    msg2 = IncomingWhatsAppWebhook(
        messageId="msg_album_002",
        chatJid=settings.CLASS_GROUP_JID,
        senderJid="2348011112222@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()) + 1,
        text="",
        media=IncomingMediaInfo(
            mimeType="image/jpeg",
            fileName="page2.jpg",
            fileSize=len(sample2_b64),
            dataBase64=sample2_b64,
        ),
    )

    res2 = await orchestrator.handle_incoming_message(msg2, test_session)
    assert res2["status"] == "media_grouped"
    assert res2["assignment_id"] == assign_id

    # Verify assignment has 2 attachments in DB
    assign_repo = AssignmentRepository(test_session)
    assign = await assign_repo.get_by_id(assign_id)
    assert len(assign.attachments) == 2
    assert {a.file_name for a in assign.attachments} == {"page1.jpg", "page2.jpg"}


@pytest.mark.asyncio
async def test_media_grouping_does_not_combine_conflicting_courses(test_session, mock_gateway_client):
    import base64
    from backend.app.schemas.webhook import IncomingMediaInfo
    from backend.app.core.config import settings

    orchestrator = WhatsAppOrchestrator(gateway_client=mock_gateway_client)
    sample_b64 = base64.b64encode(b"fake image bytes").decode("ascii")

    msg1 = IncomingWhatsAppWebhook(
        messageId="msg_diff_001",
        chatJid=settings.CLASS_GROUP_JID,
        senderJid="2348011112222@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="CSC 301 Assignment 1",
        media=IncomingMediaInfo(
            mimeType="image/jpeg",
            fileName="csc301.jpg",
            fileSize=len(sample_b64),
            dataBase64=sample_b64,
        ),
    )

    res1 = await orchestrator.handle_incoming_message(msg1, test_session)
    assert res1["status"] == "queued_for_review"

    # Message 2 mentions MTH 202 explicitly
    msg2 = IncomingWhatsAppWebhook(
        messageId="msg_diff_002",
        chatJid=settings.CLASS_GROUP_JID,
        senderJid="2348011112222@s.whatsapp.net",
        isGroup=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()) + 1,
        text="Also lecturer dropped MTH 202 Linear Algebra homework due Tuesday",
        media=IncomingMediaInfo(
            mimeType="image/jpeg",
            fileName="mth202.jpg",
            fileSize=len(sample_b64),
            dataBase64=sample_b64,
        ),
    )

    res2 = await orchestrator.handle_incoming_message(msg2, test_session)
    assert res2["status"] == "queued_for_review"
    # Separate assignment was created!
    assert res2["assignment_id"] != res1["assignment_id"]


@pytest.mark.asyncio
async def test_student_private_assignment_forwarding(test_session, mock_gateway_client):
    from backend.app.repositories.admin_repo import AdminRepository
    from backend.app.services.assignment_review.review_service import ReviewService

    admin_repo = AdminRepository(test_session)
    await admin_repo.add_admin("2348000000000@s.whatsapp.net", name="Class Rep")
    await test_session.commit()

    review_service = ReviewService(gateway_client=mock_gateway_client)
    orchestrator = WhatsAppOrchestrator(
        review_service=review_service,
        gateway_client=mock_gateway_client,
    )

    # Student forwards assignment in private 1-on-1 chat with bot
    student_jid = "2348099887766@s.whatsapp.net"
    msg = IncomingWhatsAppWebhook(
        messageId="msg_pvt_fwd_001",
        chatJid=student_jid,
        senderJid=student_jid,
        senderName="Ade",
        isGroup=False,
        isForwarded=True,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        text="Assignment: CSC 301 Write a doubly linked list in C. Due Friday.",
    )

    res = await orchestrator.handle_incoming_message(msg, test_session)
    assert res["status"] == "queued_for_review"
    assert res["course"] == "CSC 301"

    # Verify both:
    # 1. Admin was notified for review
    # 2. Student received acknowledgement in private chat
    assert mock_gateway_client.send_text.called
    calls = [c[1] for c in mock_gateway_client.send_text.call_args_list]

    admin_call = next((c for c in calls if c["to"] == "2348000000000@s.whatsapp.net"), None)
    assert admin_call is not None
    assert "CSC 301" in admin_call["text"]

    student_call = next((c for c in calls if c["to"] == student_jid), None)
    assert student_call is not None
    assert "Assignment Received" in student_call["text"]
