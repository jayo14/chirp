import logging
from typing import Optional, Dict, Any
import httpx
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppGatewayClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.WHATSAPP_GATEWAY_URL).rstrip("/")
        self.secret = secret or settings.WHATSAPP_GATEWAY_SECRET
        self.headers = {
            "Content-Type": "application/json",
            "X-Gateway-Secret": self.secret,
        }

    async def send_text(
        self,
        to: str,
        text: str,
        quoted_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/send/text"
        payload = {
            "to": to,
            "text": text,
            "quotedMessageId": quoted_message_id,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send WhatsApp text to {to}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_media(
        self,
        to: str,
        media_type: str,  # "image" or "document"
        file_url: Optional[str] = None,
        media_base64: Optional[str] = None,
        file_name: Optional[str] = None,
        caption: Optional[str] = None,
        quoted_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/send/media"
        payload = {
            "to": to,
            "mediaType": media_type,
            "mediaUrl": file_url,
            "mediaBase64": media_base64,
            "fileName": file_name,
            "caption": caption,
            "quotedMessageId": quoted_message_id,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send WhatsApp media to {to}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        url = f"{self.base_url}/status"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=self.headers)
                return resp.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
