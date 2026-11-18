from typing import Optional
from pydantic import BaseModel


class SendTextRequest(BaseModel):
    to: str
    text: str
    quotedMessageId: Optional[str] = None


class SendMediaRequest(BaseModel):
    to: str
    mediaUrl: Optional[str] = None
    mediaBase64: Optional[str] = None
    mediaType: str  # "image" or "document"
    fileName: Optional[str] = None
    caption: Optional[str] = None
    quotedMessageId: Optional[str] = None


class GatewaySendResponse(BaseModel):
    success: bool
    messageId: Optional[str] = None
    error: Optional[str] = None
