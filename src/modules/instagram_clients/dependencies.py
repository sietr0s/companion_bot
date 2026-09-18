"""DI for instagram_clients HTTP and InstagramClientManager."""

from fastapi import Depends

from src.bus import get_producer
from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager

from src.modules.instagram_clients.repository import (
    InstagramAccountRepository,
    InstagramChatStateRepository,
    InstagramSettingsRepository,
)
from src.modules.instagram_clients.services import (
    InstagramAccountService,
    InstagramChatStateService,
    InstagramSettingsService,
)


_instagram_client_manager: InstagramClientManager | None = None


def configure_instagram_client_manager(manager: InstagramClientManager) -> None:
    global _instagram_client_manager
    _instagram_client_manager = manager


def get_instagram_client_manager() -> InstagramClientManager:
    if _instagram_client_manager is None:
        raise RuntimeError(
            "InstagramClientManager не сконфигурирован. "
            "Создайте ApplicationContainer или вызовите configure_instagram_client_manager."
        )
    return _instagram_client_manager


def get_instagram_account_repository() -> InstagramAccountRepository:
    return InstagramAccountRepository()


def get_instagram_settings_repository() -> InstagramSettingsRepository:
    return InstagramSettingsRepository()


def get_instagram_chat_state_repository() -> InstagramChatStateRepository:
    return InstagramChatStateRepository()


def get_instagram_settings_service(
    repo: InstagramSettingsRepository = Depends(get_instagram_settings_repository),
) -> InstagramSettingsService:
    return InstagramSettingsService(repository=repo)


def build_instagram_account_service(
    client_manager: InstagramClientManager | None = None,
) -> InstagramAccountService:
    return InstagramAccountService(
        repository=get_instagram_account_repository(),
        settings_service=InstagramSettingsService(get_instagram_settings_repository()),
        client_manager=client_manager or get_instagram_client_manager(),
        message_bus=get_producer(),
        chat_state_repository=get_instagram_chat_state_repository(),
    )


def get_instagram_account_service(
    repo: InstagramAccountRepository = Depends(get_instagram_account_repository),
    settings: InstagramSettingsService = Depends(get_instagram_settings_service),
) -> InstagramAccountService:
    return InstagramAccountService(
        repository=repo,
        settings_service=settings,
        client_manager=get_instagram_client_manager(),
        message_bus=get_producer(),
        chat_state_repository=get_instagram_chat_state_repository(),
    )


def get_instagram_chat_state_service(
    repo: InstagramChatStateRepository = Depends(get_instagram_chat_state_repository),
) -> InstagramChatStateService:
    return InstagramChatStateService(repository=repo)
