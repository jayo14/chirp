import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    DEBUG: bool = True
    TIMEZONE: str = "Africa/Lagos"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_SECRET_KEY: str = "chirp-insecure-secret-key-change-in-production"
    ADMIN_API_KEY: str = "chirp-admin-secret-key-change-in-production"

    # Gateway
    WHATSAPP_GATEWAY_URL: str = "http://localhost:3000"
    WHATSAPP_GATEWAY_SECRET: str = "chirp-shared-gateway-secret-key-12345"

    # WhatsApp Group & Admin
    CLASS_GROUP_JID: str = "120363028392039203@g.us"
    INITIAL_ADMIN_JIDS: str = "2348000000000@s.whatsapp.net"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./chirp.db"

    # Storage
    STORAGE_PROVIDER: str = "local"  # "local" or "supabase"
    LOCAL_STORAGE_DIR: str = "./uploads"
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "chirp-attachments"

    # AI
    AI_PROVIDER: str = "mock"  # "gemini", "openai", "mock"
    AI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-1.5-flash"

    # Reminder & Digests
    DEFAULT_REMINDER_HOURS: int = 24
    WEEKLY_DIGEST_DAY: str = "sunday"
    WEEKLY_DIGEST_TIME: str = "17:00"
    SCHEDULER_INTERVAL_SECONDS: int = 60

    @property
    def admin_jid_list(self) -> List[str]:
        if not self.INITIAL_ADMIN_JIDS:
            return []
        return [jid.strip() for jid in self.INITIAL_ADMIN_JIDS.split(",") if jid.strip()]


settings = Settings()
