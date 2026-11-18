from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.settings import BotSetting


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        setting = await self.session.get(BotSetting, key)
        if setting:
            return setting.value
        return default

    async def set(self, key: str, value: str, description: Optional[str] = None) -> BotSetting:
        setting = await self.session.get(BotSetting, key)
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = BotSetting(key=key, value=value, description=description)
            self.session.add(setting)
        await self.session.flush()
        return setting
