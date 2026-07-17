"""
DI-зависимости модуля telegram_clients.

Фабрики для внедрения TelegramClientService и
TelegramSettingsService через FastAPI Depends.
"""
import logging

from fastapi import Depends

from src.bus import get_producer
from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.services import TelegramAccountService, TelegramSettingsService

logger = logging.getLogger(__name__)

# Глобальный экземпляр менеджера (singleton)
_telegram_client_manager: TelegramClientManager | None = None


def get_telegram_account_repository() -> TelegramAccountRepository:
    """Фабрика репозитория Telegram-аккаунтов."""
    return TelegramAccountRepository()


def get_telegram_settings_repository() -> TelegramSettingsRepository:
    """Фабрика репозитория настроек Telegram."""
    return TelegramSettingsRepository()


def get_telegram_chat_state_repository() -> TelegramChatStateRepository:
    """Фабрика репозитория состояний чтения чатов Telegram."""
    return TelegramChatStateRepository()


def get_telegram_account_service(
        repo: TelegramAccountRepository = Depends(get_telegram_account_repository),
        settings_repo: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
        chat_state_repo: TelegramChatStateRepository = Depends(get_telegram_chat_state_repository),
) -> TelegramAccountService:
    """Фабрика сервиса Telegram-Aккаунтов."""
    return TelegramAccountService(
        repository=repo,
        message_bus=get_producer(),
        client_manager=get_telegram_client_manager(),
        settings_repository=settings_repo,
        chat_state_repository=chat_state_repo,
    )


def get_telegram_settings_service(
        repo: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
) -> TelegramSettingsService:
    """Фабрика сервиса Telegram-Настроек."""
    return TelegramSettingsService(
        repository=repo,
        message_bus=get_producer(),
    )


def get_telegram_client_service_factory() -> TelegramAccountService:
    """Фабрика сервиса Telegram-клиентов."""
    return TelegramAccountService(
        repository=get_telegram_account_repository(),
        message_bus=get_producer(),
        client_manager=get_telegram_client_manager(),
        settings_repository=get_telegram_settings_repository(),
        chat_state_repository=get_telegram_chat_state_repository(),
    )


def get_telegram_client_manager() -> TelegramClientManager:
    """
    Создать или вернуть существующий TelegramClientManager.

    Returns:
        Singleton-экземпляр TelegramClientManager
    """
    global _telegram_client_manager
    if _telegram_client_manager is None:
        _telegram_client_manager = TelegramClientManager()
        logger.info("Создан новый экземпляр TelegramClientManager")
    return _telegram_client_manager
