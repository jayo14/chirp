from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from backend.app.core.database import get_db
from backend.app.integrations.whatsapp_gateway import WhatsAppGatewayClient

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    gateway_client = WhatsAppGatewayClient()
    gateway_status = await gateway_client.get_status()

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "service": "chirp-backend",
        "database": db_status,
        "whatsapp_gateway": gateway_status,
    }
