from backend.app.core.config import settings
from backend.app.integrations.storage.base import StorageProvider
from backend.app.integrations.storage.local import LocalStorageProvider
from backend.app.integrations.storage.supabase import SupabaseStorageProvider


def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "supabase" and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        return SupabaseStorageProvider()
    return LocalStorageProvider()
