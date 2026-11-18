from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.admin import Administrator


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_admin(self, sender_jid: str, initial_admin_jids: List[str]) -> bool:
        clean_jid = sender_jid.strip().lower()

        # Check in initial config admins
        for configured in initial_admin_jids:
            conf_clean = configured.strip().lower()
            if conf_clean == clean_jid or clean_jid.startswith(conf_clean.split("@")[0]):
                return True

        # Check in database
        stmt = select(Administrator).where(
            Administrator.is_active == True
        )
        result = await self.session.execute(stmt)
        admins = result.scalars().all()
        for admin in admins:
            adm_clean = admin.phone_or_jid.strip().lower()
            if adm_clean == clean_jid or clean_jid.startswith(adm_clean.split("@")[0]):
                return True

        return False

    async def get_all_active_admin_jids(self, initial_admin_jids: List[str]) -> List[str]:
        jids = set(initial_admin_jids)
        stmt = select(Administrator.phone_or_jid).where(Administrator.is_active == True)
        result = await self.session.execute(stmt)
        for row in result.scalars().all():
            jids.add(row)
        return [j for j in jids if j]

    async def add_admin(self, phone_or_jid: str, name: Optional[str] = None, role: str = "admin") -> Administrator:
        admin = Administrator(
            phone_or_jid=phone_or_jid.strip(),
            name=name,
            role=role,
            is_active=True,
        )
        self.session.add(admin)
        await self.session.flush()
        return admin
