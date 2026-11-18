from sqlalchemy import Column, String, Text
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin


class BotSetting(Base, TimestampMixin):
    __tablename__ = "bot_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
