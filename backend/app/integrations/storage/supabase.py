import uuid
import logging
from typing import Tuple
import httpx
from backend.app.core.config import settings
from backend.app.integrations.storage.base import StorageProvider

logger = logging.getLogger(__name__)


class SupabaseStorageProvider(StorageProvider):
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else ""
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    async def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
    ) -> Tuple[str, str]:
        if not self.supabase_url or not self.service_role_key:
            raise ValueError("Supabase storage is not configured with URL or Service Role Key")

        unique_prefix = uuid.uuid4().hex[:12]
        storage_path = f"{unique_prefix}_{file_name}"
        upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_path}"

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": mime_type,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(upload_url, content=file_bytes, headers=headers)
            resp.raise_for_status()

        public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{storage_path}"
        return public_url, storage_path
