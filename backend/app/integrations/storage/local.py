import os
import re
import uuid
from typing import Tuple, Optional
from backend.app.core.config import settings
from backend.app.integrations.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = settings.LOCAL_STORAGE_DIR):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _sanitize_filename(self, file_name: str) -> str:
        # Extract base name to strip directory components
        base = os.path.basename(file_name)
        # Remove non-whitelisted characters
        cleaned = re.sub(r"[^\w\.-]", "_", base).lstrip(".")
        if not cleaned or cleaned.replace(".", "") == "":
            cleaned = "attachment.bin"
        return cleaned

    def _resolve_and_verify_path(self, relative_or_absolute_path: str) -> str:
        if os.path.isabs(relative_or_absolute_path):
            target = os.path.abspath(relative_or_absolute_path)
        else:
            target = os.path.abspath(os.path.join(self.base_dir, relative_or_absolute_path))

        # Check that target stays strictly within base_dir
        if os.path.commonpath([self.base_dir, target]) != self.base_dir:
            raise ValueError(f"Path traversal attempt detected: {relative_or_absolute_path}")

        return target

    async def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
    ) -> Tuple[str, str]:
        safe_name = self._sanitize_filename(file_name)
        unique_prefix = uuid.uuid4().hex[:12]
        file_basename = f"{unique_prefix}_{safe_name}"
        full_path = self._resolve_and_verify_path(file_basename)

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        access_url = f"file://{full_path}"
        return access_url, full_path

    async def read_file(self, storage_path: str) -> Optional[bytes]:
        safe_path = self._resolve_and_verify_path(storage_path)
        if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
            return None
        with open(safe_path, "rb") as f:
            return f.read()
