import base64
import io
import pytest
import pypdf
from backend.app.schemas.webhook import IncomingMediaInfo
from backend.app.services.media_processing.media_service import MediaService
from backend.app.integrations.storage.local import LocalStorageProvider


def create_digital_pdf_base64() -> str:
    writer = pypdf.PdfWriter()
    # Add a page with substantial text
    page = writer.add_blank_page(width=300, height=300)
    # We can use pypdf annotation or write text
    # Or in pypdf, writer with metadata or annotations
    buf = io.BytesIO()
    writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def create_blank_or_scanned_pdf_base64() -> str:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.mark.asyncio
async def test_scanned_pdf_renders_page_images(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    media_service = MediaService(storage_provider=storage)

    pdf_b64 = create_blank_or_scanned_pdf_base64()
    media_info = IncomingMediaInfo(
        mimeType="application/pdf",
        fileName="scanned_assignment.pdf",
        fileSize=len(pdf_b64),
        dataBase64=pdf_b64,
    )

    result = await media_service.process_incoming_media(media_info)

    # Scanned PDF detection
    assert result.is_scanned is True
    assert len(result.rendered_images) >= 1
    # Verify rendered image is a valid base64 JPEG
    img_bytes = base64.b64decode(result.rendered_images[0])
    assert img_bytes[:2] == b"\xff\xd8"  # JPEG header

    # Original PDF preserved in storage
    saved_bytes = await storage.read_file(result.storage_path)
    assert saved_bytes is not None
    assert saved_bytes.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_tuple_unpacking_compatibility(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    media_service = MediaService(storage_provider=storage)

    pdf_b64 = create_blank_or_scanned_pdf_base64()
    media_info = IncomingMediaInfo(
        mimeType="application/pdf",
        fileName="quiz.pdf",
        fileSize=len(pdf_b64),
        dataBase64=pdf_b64,
    )

    # Verify tuple unpacking works seamlessly for backward compatibility
    file_url, storage_path, extracted_text = await media_service.process_incoming_media(media_info)
    assert file_url is not None
    assert storage_path is not None


@pytest.mark.asyncio
async def test_malformed_pdf_does_not_crash(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    media_service = MediaService(storage_provider=storage)

    corrupt_b64 = base64.b64encode(b"%PDF-1.4 CORRUPTED DATA NOT VALID PDF").decode("ascii")
    media_info = IncomingMediaInfo(
        mimeType="application/pdf",
        fileName="broken.pdf",
        fileSize=len(corrupt_b64),
        dataBase64=corrupt_b64,
    )

    result = await media_service.process_incoming_media(media_info)
    assert result.extracted_text is None
    # Original file is preserved
    assert await storage.read_file(result.storage_path) is not None
