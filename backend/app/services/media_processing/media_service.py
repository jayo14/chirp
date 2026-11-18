import base64
import io
import logging
from typing import Optional, List, Tuple
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import pypdfium2 as pdfium
from PIL import Image

from backend.app.schemas.webhook import IncomingMediaInfo
from backend.app.integrations.storage.base import StorageProvider
from backend.app.integrations.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)

MAX_RENDER_PAGES = 3
MIN_DIGITAL_TEXT_CHARS = 100
MAX_TEXT_EXTRACT_CHARS = 50000


class MediaProcessingResult:
    def __init__(
        self,
        file_url: str,
        storage_path: str,
        extracted_text: Optional[str] = None,
        rendered_images: Optional[List[str]] = None,
        is_scanned: bool = False,
    ):
        self.file_url = file_url
        self.storage_path = storage_path
        self.extracted_text = extracted_text
        self.rendered_images = rendered_images or []
        self.is_scanned = is_scanned

    def __iter__(self):
        """Allows unpacking: file_url, storage_path, extracted_text = result"""
        return iter((self.file_url, self.storage_path, self.extracted_text))


class MediaService:
    def __init__(self, storage_provider: Optional[StorageProvider] = None):
        self.storage_provider = storage_provider or get_storage_provider()

    async def process_incoming_media(
        self,
        media_info: IncomingMediaInfo,
    ) -> MediaProcessingResult:
        """
        Processes incoming media:
        1. Decodes base64 content safely.
        2. If PDF, extracts embedded digital text first.
        3. If scanned PDF (minimal or missing embedded text), renders pages to JPEG images
           for vision analysis (handwriting, math, diagrams).
        4. Preserves and persists the original unaltered file in storage.
        Returns: MediaProcessingResult
        """
        try:
            file_bytes = base64.b64decode(media_info.dataBase64)
        except Exception as e:
            logger.error(f"Failed to decode media base64: {str(e)}")
            raise ValueError(f"Invalid base64 media payload: {str(e)}")

        file_name = media_info.fileName or ("document.pdf" if "pdf" in media_info.mimeType else "attachment.jpg")
        mime_type = media_info.mimeType

        extracted_text: Optional[str] = None
        rendered_images: List[str] = []
        is_scanned = False

        is_pdf = "pdf" in mime_type.lower() or file_name.lower().endswith(".pdf")

        if is_pdf:
            # 1. Extract embedded digital text
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                pages_text = []
                for idx, page in enumerate(reader.pages[:10]):  # Inspect up to first 10 pages
                    try:
                        p_txt = page.extract_text()
                        if p_txt:
                            pages_text.append(f"--- Page {idx + 1} ---\n{p_txt.strip()}")
                    except Exception as pe:
                        logger.warning(f"Error extracting text from PDF page {idx + 1}: {pe}")

                if pages_text:
                    full_text = "\n\n".join(pages_text)
                    extracted_text = full_text[:MAX_TEXT_EXTRACT_CHARS]
            except (PdfReadError, Exception) as e:
                logger.warning(f"Malformed or encrypted PDF encountered: {str(e)}")

            # 2. Check if scanned or image-based PDF
            has_sufficient_text = bool(extracted_text and len(extracted_text.strip()) >= MIN_DIGITAL_TEXT_CHARS)

            if not has_sufficient_text:
                is_scanned = True
                logger.info(f"PDF '{file_name}' appears scanned or image-based; rendering pages to images for vision extraction.")
                try:
                    pdf_doc = pdfium.PdfDocument(io.BytesIO(file_bytes))
                    num_pages = min(len(pdf_doc), MAX_RENDER_PAGES)
                    for page_idx in range(num_pages):
                        page = pdf_doc[page_idx]
                        # Render at scale 2.0 (approx 144 DPI) for clear legibility of equations and handwriting
                        pil_img = page.render(scale=2.0).to_pil()
                        img_buf = io.BytesIO()
                        pil_img.save(img_buf, format="JPEG", quality=85)
                        b64_str = base64.b64encode(img_buf.getvalue()).decode("ascii")
                        rendered_images.append(b64_str)
                except Exception as re:
                    logger.error(f"Failed to render PDF pages with pypdfium2: {str(re)}")

        # 3. Preserve original file to storage provider
        file_url, storage_path = await self.storage_provider.save_file(
            file_bytes=file_bytes,
            file_name=file_name,
            mime_type=mime_type,
        )

        return MediaProcessingResult(
            file_url=file_url,
            storage_path=storage_path,
            extracted_text=extracted_text,
            rendered_images=rendered_images,
            is_scanned=is_scanned,
        )
