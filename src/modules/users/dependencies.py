"""DI модуля users."""

from fastapi import Depends

from src.bus import get_producer
from src.bus.interface import MessageProducer
from src.modules.users.repository import UserRepository
from src.modules.users.service import UserService


def get_user_repository() -> UserRepository:
    return UserRepository()


def build_user_service(message_bus: MessageProducer | None = None) -> UserService:
    return UserService(
        repository=UserRepository(),
        message_bus=message_bus or get_producer(),
    )


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repository=repo, message_bus=get_producer())
