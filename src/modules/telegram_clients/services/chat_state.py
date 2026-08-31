from src.base.service import BaseService
from src.modules.telegram_clients.models import TelegramChatState
from src.modules.telegram_clients.repository import TelegramChatStateRepository


class TelegramChatStateService(BaseService[TelegramChatStateRepository, TelegramChatState]):
    def __init__(self, repository: TelegramChatStateRepository) -> None:
        super().__init__(repository)
