"""DI for instagram_clients HTTP. Manager configure arrives in a later task."""

from fastapi import Depends

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


def get_instagram_account_service(
    repo: InstagramAccountRepository = Depends(get_instagram_account_repository),
    settings: InstagramSettingsService = Depends(get_instagram_settings_service),
) -> InstagramAccountService:
    return InstagramAccountService(repository=repo, settings_service=settings)


def get_instagram_chat_state_service(
    repo: InstagramChatStateRepository = Depends(get_instagram_chat_state_repository),
) -> InstagramChatStateService:
    return InstagramChatStateService(repository=repo)
