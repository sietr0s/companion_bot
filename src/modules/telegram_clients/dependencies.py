"""
DI-зависимости модуля telegram_clients.

Фабрики для внедрения TelegramClientService и
TelegramSettingsService через FastAPI Depends.
"""

from fastapi import Depends

from src.bus.interface import MessageBus
from src.bus.providers import get_message_bus
from src.core.telegram_manager import get_telegram_client_manager
from src.modules.telegram_clients.client_manager import TelegramClientManager
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.service import TelegramClientService


def get_telegram_account_repository() -> TelegramAccountRepository:
    """Фабрика репозитория Telegram-аккаунтов."""
    return TelegramAccountRepository()


def get_telegram_settings_repository() -> TelegramSettingsRepository:
    """Фабрика репозитория настроек Telegram."""
    return TelegramSettingsRepository()


def get_telegram_chat_state_repository() -> TelegramChatStateRepository:
    """Фабрика репозитория состояний чтения чатов Telegram."""
    return TelegramChatStateRepository()


def get_client_manager() -> TelegramClientManager:
    """
    Провайдер TelegramClientManager.

    Возвращает глобальный экземпляр client_manager.
    """
    return get_telegram_client_manager()


def get_telegram_client_service(
    repo: TelegramAccountRepository = Depends(get_telegram_account_repository),
    bus: MessageBus = Depends(get_message_bus),
    manager: TelegramClientManager = Depends(get_client_manager),
    settings_repo: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
    chat_state_repo: TelegramChatStateRepository = Depends(get_telegram_chat_state_repository),
) -> TelegramClientService:
    """Фабрика сервиса Telegram-клиентов."""
    return TelegramClientService(
        repository=repo,
        message_bus=bus,
        client_manager=manager,
        settings_repository=settings_repo,
        chat_state_repository=chat_state_repo,
    )


def get_telegram_settings_service(
    repo: TelegramAccountRepository = Depends(get_telegram_account_repository),
    bus: MessageBus = Depends(get_message_bus),
    manager: TelegramClientManager = Depends(get_client_manager),
    settings_repo: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
    chat_state_repo: TelegramChatStateRepository = Depends(
        get_telegram_chat_state_repository
    ),
) -> TelegramClientService:
    """Фабрика сервиса для работы с настройками Telegram."""
    return TelegramClientService(
        repository=repo,
        message_bus=bus,
        client_manager=manager,
        settings_repository=settings_repo,
        chat_state_repository=chat_state_repo,
    )
