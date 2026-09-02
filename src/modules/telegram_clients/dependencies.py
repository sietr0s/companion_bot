"""
DI-зависимости модуля telegram_clients.

Менеджер клиентов живёт в ApplicationContainer и
регистрируется через configure_telegram_client_manager.
"""

from fastapi import Depends

from src.bus import get_producer
from src.modules.telegram_clients.adapters.client_manager import TelegramClientManager
from src.modules.telegram_clients.repository import (
    TelegramAccountRepository,
    TelegramChatStateRepository,
    TelegramSettingsRepository,
)
from src.modules.telegram_clients.services import (
    TelegramAccountService,
    TelegramChatStateService,
    TelegramSettingsService,
)

_telegram_client_manager: TelegramClientManager | None = None


def configure_telegram_client_manager(manager: TelegramClientManager) -> None:
    """Зафиксировать экземпляр менеджера из контейнера приложения."""
    global _telegram_client_manager
    _telegram_client_manager = manager


def get_telegram_client_manager() -> TelegramClientManager:
    if _telegram_client_manager is None:
        raise RuntimeError(
            "TelegramClientManager не сконфигурирован. "
            "Создайте ApplicationContainer или вызовите configure_telegram_client_manager."
        )
    return _telegram_client_manager


def get_telegram_account_repository() -> TelegramAccountRepository:
    return TelegramAccountRepository()


def get_telegram_settings_repository() -> TelegramSettingsRepository:
    return TelegramSettingsRepository()


def get_telegram_chat_state_repository() -> TelegramChatStateRepository:
    return TelegramChatStateRepository()


def get_telegram_account_service(
    repo: TelegramAccountRepository = Depends(get_telegram_account_repository),
    settings_repo: TelegramSettingsRepository = Depends(
        get_telegram_settings_repository
    ),
    chat_state_repo: TelegramChatStateRepository = Depends(
        get_telegram_chat_state_repository
    ),
    client_manager: TelegramClientManager = Depends(get_telegram_client_manager),
) -> TelegramAccountService:
    return TelegramAccountService(
        repository=repo,
        message_bus=get_producer(),
        client_manager=client_manager,
        settings_repository=settings_repo,
        chat_state_repository=chat_state_repo,
    )


def get_telegram_settings_service(
    repo: TelegramSettingsRepository = Depends(get_telegram_settings_repository),
) -> TelegramSettingsService:
    return TelegramSettingsService(repository=repo)


def get_telegram_chat_state_service(
    repo: TelegramChatStateRepository = Depends(get_telegram_chat_state_repository),
) -> TelegramChatStateService:
    return TelegramChatStateService(repository=repo)


def get_telegram_client_service_factory(
    client_manager: TelegramClientManager | None = None,
) -> TelegramAccountService:
    return TelegramAccountService(
        repository=get_telegram_account_repository(),
        message_bus=get_producer(),
        client_manager=client_manager or get_telegram_client_manager(),
        settings_repository=get_telegram_settings_repository(),
        chat_state_repository=get_telegram_chat_state_repository(),
    )
