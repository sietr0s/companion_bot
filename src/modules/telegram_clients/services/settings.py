import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.modules.telegram_clients.models import (
    TelegramSettings,
)
from src.modules.telegram_clients.repository import (
    TelegramSettingsRepository,
)

logger = logging.getLogger(__name__)

class TelegramSettingsService(
    BaseService[TelegramSettingsRepository, TelegramSettings]
):
    def __init__(
            self,
            repository: TelegramSettingsRepository,
            message_bus: MessageProducer
    ):
        super().__init__(repository)
        self.message_bus = message_bus

    async def create_default_settings(
            self, session: AsyncSession, account_id: uuid.UUID
    ) -> TelegramSettings:
        """Создать настройки по умолчанию."""

        default_data = {
            "account_id": account_id,
            "use_whitelist": True,
            "whitelist_chat_ids": [],
        }
        return await self.repository.create(session, default_data)

    async def add_chat_to_whitelist(self, session: AsyncSession, account_id: uuid.UUID, chat_id: int) -> TelegramSettings:
        settings = await self.repository.get_by_account_id(session, account_id)
        if settings is None:
            settings = await self.create_default_settings(session, account_id)
        chat_ids = {int(value) for value in (settings.whitelist_chat_ids or [])}
        chat_ids.add(chat_id)
        return await self.repository.update(session, settings, {"whitelist_chat_ids": sorted(chat_ids)})

    async def remove_chat_from_whitelist(self, session: AsyncSession, account_id: uuid.UUID, chat_id: int) -> TelegramSettings:
        settings = await self.repository.get_by_account_id(session, account_id)
        if settings is None:
            settings = await self.create_default_settings(session, account_id)
        chat_ids = [int(value) for value in (settings.whitelist_chat_ids or []) if int(value) != chat_id]
        return await self.repository.update(session, settings, {"whitelist_chat_ids": chat_ids})
