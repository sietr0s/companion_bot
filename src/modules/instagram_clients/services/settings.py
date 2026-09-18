import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.modules.instagram_clients.models import InstagramSettings
from src.modules.instagram_clients.repository import InstagramSettingsRepository


class InstagramSettingsService(BaseService[InstagramSettingsRepository, InstagramSettings]):
    def __init__(self, repository: InstagramSettingsRepository):
        super().__init__(repository)

    async def create_default_settings(
        self, session: AsyncSession, account_id: uuid.UUID
    ) -> InstagramSettings:
        existing = await self.repository.get_by_account_id(session, account_id)
        if existing is not None:
            return existing
        return await self.repository.create(
            session,
            {
                "account_id": account_id,
                "use_whitelist": True,
                "whitelist_user_pks": [],
            },
        )

    async def add_user_to_whitelist(
        self, session: AsyncSession, account_id: uuid.UUID, user_pk: int
    ) -> InstagramSettings:
        settings = await self.create_default_settings(session, account_id)
        pks = {int(value) for value in (settings.whitelist_user_pks or [])}
        pks.add(int(user_pk))
        return await self.repository.update(
            session, settings, {"whitelist_user_pks": sorted(pks)}
        )

    async def remove_user_from_whitelist(
        self, session: AsyncSession, account_id: uuid.UUID, user_pk: int
    ) -> InstagramSettings:
        settings = await self.create_default_settings(session, account_id)
        pks = [
            int(value)
            for value in (settings.whitelist_user_pks or [])
            if int(value) != int(user_pk)
        ]
        return await self.repository.update(session, settings, {"whitelist_user_pks": pks})
