import secrets
from fastapi import Header, HTTPException, status
from backend.app.core.config import settings


async def verify_gateway_secret(
    x_gateway_secret: str = Header(..., description="Secret shared between WhatsApp Gateway and Backend")
) -> str:
    if not x_gateway_secret or not secrets.compare_digest(
        x_gateway_secret, settings.WHATSAPP_GATEWAY_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Gateway-Secret header",
        )
    return x_gateway_secret
