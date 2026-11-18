import secrets
from typing import Optional
from fastapi import Header, HTTPException, status
from backend.app.core.config import settings


async def verify_gateway_secret(
    x_gateway_secret: Optional[str] = Header(None, description="Secret shared between WhatsApp Gateway and Backend")
) -> str:
    if not x_gateway_secret or not secrets.compare_digest(
        x_gateway_secret, settings.WHATSAPP_GATEWAY_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Gateway-Secret header",
        )
    return x_gateway_secret


async def verify_admin_auth(
    x_admin_api_key: Optional[str] = Header(None, description="Administrative API Key"),
    authorization: Optional[str] = Header(None, description="Bearer token authentication"),
) -> str:
    provided_key = None

    if x_admin_api_key:
        provided_key = x_admin_api_key
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key or not secrets.compare_digest(provided_key, settings.ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing administrator credentials",
        )

    return provided_key
