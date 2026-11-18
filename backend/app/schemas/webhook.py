from typing import Optional
from pydantic import BaseModel, Field


class QuotedMessageInfo(BaseModel):
    messageId: str
    senderJid: str
    text: Optional[str] = None


class IncomingMediaInfo(BaseModel):
    fileName: Optional[str] = None
    mimeType: str
    fileSize: Optional[int] = None
    dataBase64: str
    caption: Optional[str] = None


class IncomingWhatsAppWebhook(BaseModel):
    messageId: str
    chatJid: str
    senderJid: str
    senderName: Optional[str] = None
    isGroup: bool
    isForwarded: bool = False
    timestamp: int
    text: Optional[str] = None
    caption: Optional[str] = None
    quotedMessage: Optional[QuotedMessageInfo] = None
    media: Optional[IncomingMediaInfo] = None

    @property
    def full_text(self) -> str:
        parts = []
        if self.text:
            parts.append(self.text)
        if self.caption and self.caption != self.text:
            parts.append(self.caption)
        return "\n".join(parts).strip()
