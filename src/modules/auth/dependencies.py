"""
DI-зависимости модуля auth.

Фабрики для внедрения AuthService и AuthRepository
через FastAPI Depends.
"""

from fastapi import Depends

from src.bus.interface import MessageBus
from src.bus.providers import get_message_bus
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService


def get_auth_repository() -> AuthRepository:
    """Фабрика репозитория авторизации."""
    return AuthRepository()


def get_auth_service(
    repo: AuthRepository = Depends(get_auth_repository),
    bus: MessageBus = Depends(get_message_bus),
) -> AuthService:
    """Фабрика сервиса авторизации с внедрением репозитория и шины."""
    return AuthService(repository=repo, message_bus=bus)
