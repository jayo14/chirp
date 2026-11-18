from abc import ABC, abstractmethod
from typing import Tuple, Optional


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

    @abstractmethod
    async def read_file(self, storage_path: str) -> Optional[bytes]:
        """
        Reads and returns the raw file bytes for a given storage path.
        """
        pass
