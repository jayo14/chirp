from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import verify_gateway_secret
from backend.app.schemas.webhook import IncomingWhatsAppWebhook
from backend.app.services.orchestrator import WhatsAppOrchestrator

router = APIRouter(tags=["Webhook"])
orchestrator = WhatsAppOrchestrator()


@router.post(
    "/api/v1/webhook/whatsapp",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_gateway_secret)],
)
async def receive_whatsapp_webhook(
    payload: IncomingWhatsAppWebhook,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives incoming WhatsApp message and media events forwarded from the Baileys gateway.
    Protected by X-Gateway-Secret header verification.
    """
    result = await orchestrator.handle_incoming_message(payload, db)
    return {"success": True, **result}
