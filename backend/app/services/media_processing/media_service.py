import base64
import io
import logging
from typing import Optional, Tuple
from pypdf import PdfReader
from backend.app.schemas.webhook import IncomingMediaInfo
from backend.app.integrations.storage.base import StorageProvider
from backend.app.integrations.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)


class MediaService:
    def __init__(self, storage_provider: Optional[StorageProvider] = None):
        self.storage_provider = storage_provider or get_storage_provider()

    async def process_incoming_media(
        self,
        media_info: IncomingMediaInfo,
    ) -> Tuple[str, str, Optional[str]]:
        """
        Processes incoming media:
        1. Decodes base64 content
        2. If PDF, extracts readable text
        3. Persists file to storage provider
        Returns: (file_url, storage_path, extracted_text)
        """
        try:
            file_bytes = base64.b64decode(media_info.dataBase64)
        except Exception as e:
            logger.error(f"Failed to decode media base64: {str(e)}")
            raise ValueError(f"Invalid base64 media payload: {str(e)}")

        file_name = media_info.fileName or ("document.pdf" if "pdf" in media_info.mimeType else "attachment.jpg")
        mime_type = media_info.mimeType

        # Extract text if PDF
        extracted_text: Optional[str] = None
        if "pdf" in mime_type.lower() or file_name.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(f"--- Page {idx + 1} ---\n{page_text}")
                if pages_text:
                    extracted_text = "\n".join(pages_text)
            except Exception as e:
                logger.warning(f"Could not extract text from PDF: {str(e)}")

        # Save to storage
        file_url, storage_path = await self.storage_provider.save_file(
            file_bytes=file_bytes,
            file_name=file_name,
            mime_type=mime_type,
        )

        return file_url, storage_path, extracted_text
