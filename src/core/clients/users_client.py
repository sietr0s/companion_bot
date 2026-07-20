"""
Клиент для прямого вызова сервиса пользователей.

Использует DI-фабрику для получения сервиса с общей шиной.
Session создаётся и закрывается внутри каждого метода.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import create_async_session

if TYPE_CHECKING:
    from src.modules.users.models import User
    from src.modules.users.service import UserService

logger = logging.getLogger(__name__)


class UsersClient:
    """
    Клиент для вызова методов UserService напрямую.

    Получает сервис через фабрику зависимостей (как MediaClient).
    Session создаётся и закрывается внутри каждого метода.
    """

    @staticmethod
    def _get_service() -> "UserService":
        """Получить экземпляр UserService через прямое инстанцирование."""
        from src.bus import get_producer
        from src.modules.users.repository import TelegramRepository, UserRepository
        from src.modules.users.service import UserService

        return UserService(
            repository=UserRepository(),
            telegram_repository=TelegramRepository(),
            message_bus=get_producer(),
        )

    async def resolve_email_by_auth_id(
        self,
        auth_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> str | None:
        """
        Резолвить email по auth_id через прямой вызов сервиса.

        Email хранится в модуле auth (Auth.identifier).
        Используем AuthRepository напрямую для поиска.

        Args:
            auth_id: Идентификатор пользователя из модуля auth.

        Returns:
            Email пользователя или None, если не найден.

        Raises:
            Исключения пробрасываются наверх (NotFoundError, SQLAlchemyError и т.д.).
        """
        from src.modules.auth.repository import AuthRepository

        repo = AuthRepository()
        if session is not None:
            account = await repo.get_by_id(session, auth_id)
            return account.identifier if account else None

        async with create_async_session() as own_session:
            account = await repo.get_by_id(own_session, auth_id)
            return account.identifier if account else None

    async def resolve_telegram_id_by_auth_id(
        self,
        auth_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> int:
        """Получить Telegram chat ID пользователя по ID учётной записи."""
        from src.core.exceptions import NotFoundError
        from src.modules.users.repository import TelegramRepository

        async def resolve(current_session: AsyncSession) -> int:
            telegram = await TelegramRepository().get_by_auth_id(current_session, auth_id)
            if telegram is None:
                raise NotFoundError(detail="Telegram-профиль пользователя не найден")
            return int(telegram.telegram_id)

        if session is not None:
            return await resolve(session)

        async with create_async_session() as own_session:
            return await resolve(own_session)

    async def get_profile(
        self,
        auth_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> "User":
        """
        Получить профиль пользователя по auth_id.

        Args:
            auth_id: Идентификатор пользователя из модуля auth.

        Returns:
            Объект профиля или None.

        Raises:
            Исключения пробрасываются наверх (NotFoundError, SQLAlchemyError и т.д.).
        """
        service = self._get_service()
        if session is not None:
            return await service.get_profile(session, auth_id)

        async with create_async_session() as own_session:
            return await service.get_profile(own_session, auth_id)

    async def delete_profile(
        self,
        auth_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Удалить профиль пользователя через API модуля users."""
        service = self._get_service()
        if session is not None:
            await service.delete_profile(session, auth_id)
            return

        async with create_async_session() as own_session:
            await service.delete_profile(own_session, auth_id)

    async def create_profile(
        self,
        auth_id: uuid.UUID,
        first_name: str | None = None,
        last_name: str | None = None,
        telegram_id: int | None = None,
        telegram_username: str | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        Создать профиль пользователя.

        Args:
            auth_id: Идентификатор пользователя.
            first_name: Имя.
            last_name: Фамилия.
            telegram_id: Идентификатор пользователя в Telegram.
            telegram_username: Username пользователя в Telegram.
            session: Опциональная сессия.

        Returns:
            True если создан.

        Raises:
            Исключения пробрасываются наверх (ConflictError, NotFoundError, SQLAlchemyError и т.д.).
        """
        if telegram_id is None:
            raise ValueError("telegram_id обязателен для создания Telegram-профиля")

        async def create(s: AsyncSession) -> None:
            service = self._get_service()
            profile = await service.create_user_profile(
                s,
                auth_id,
                {"first_name": first_name, "last_name": last_name},
            )
            await service.create_telegram_profile(
                s,
                profile.id,
                {
                    "telegram_id": str(telegram_id),
                    "telegram_username": telegram_username,
                    "telegram_first_name": first_name,
                    "telegram_last_name": last_name,
                },
            )

        if session is not None:
            await create(session)
            return True

        async with create_async_session() as s:
            await create(s)
            return True
