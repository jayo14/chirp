from abc import ABC, abstractmethod
from typing import Tuple


class StorageProvider(ABC):
    @abstractmethod
    async def save_file(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
    ) -> Tuple[str, str]:
        """
        Saves the file to the underlying storage.
        Returns a tuple of (public_or_access_url, storage_path).
        """
        pass
