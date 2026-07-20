"""
DI-зависимости модуля users.

Фабрики для внедрения UserService и UserRepository
через FastAPI Depends.
"""

from fastapi import Depends

from src.bus import get_producer
from src.modules.users.repository import TelegramRepository, UserRepository
from src.modules.users.service import UserService


def get_user_repository() -> UserRepository:
    """Фабрика репозитория пользователей."""
    return UserRepository()


def get_telegram_repository() -> TelegramRepository:
    """Фабрика репозитория Telegram."""
    return TelegramRepository()


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
    telegram_repo: TelegramRepository = Depends(get_telegram_repository),
) -> UserService:
    """Фабрика сервиса пользователей с внедрением репозитория и шины."""
    return UserService(
        repository=repo,
        message_bus=get_producer(),
        telegram_repository=telegram_repo,
    )
