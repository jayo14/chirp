import os
import uuid
from typing import Tuple
from backend.app.core.config import settings
from backend.app.integrations.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = settings.LOCAL_STORAGE_DIR):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
    ) -> Tuple[str, str]:
        unique_prefix = uuid.uuid4().hex[:12]
        safe_name = f"{unique_prefix}_{file_name}"
        full_path = os.path.join(self.base_dir, safe_name)

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        # In local mode, return file:// uri or relative path
        access_url = f"file://{full_path}"
        return access_url, full_path
