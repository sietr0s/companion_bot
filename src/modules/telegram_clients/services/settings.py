import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageBus
from src.modules.telegram_clients.models import (
    TelegramSettings,
)
from src.modules.telegram_clients.repository import (
    TelegramSettingsRepository,
)

logger = logging.getLogger(__name__)

class TelegramSettingsService(BaseService[TelegramSettingsRepository]):
    def __init__(
            self,
            repository: TelegramSettingsRepository,
            message_bus: MessageBus
    ):
        super().__init__(repository)
        self.message_bus = message_bus

    async def create_default_settings(
            self, session: AsyncSession, account_id: uuid.UUID
    ) -> TelegramSettings:
        """Создать настройки по умолчанию."""

        default_data = {
            "account_id": account_id,
            "read_groups": True,
            "read_personal": True,
            "read_channels": True,
            "whitelist_chat_ids": [],
        }
        return await self.repository.create(session, default_data)
