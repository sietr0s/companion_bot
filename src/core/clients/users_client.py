"""
Клиент для прямого вызова сервиса пользователей.

Использует DI-фабрику для получения сервиса с общей шиной.
Session создаётся и закрывается внутри каждого метода.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

logger = logging.getLogger(__name__)


class UsersClient:
    """
    Клиент для вызова методов UserService напрямую.

    Получает сервис через фабрику зависимостей (как MediaClient).
    Session создаётся и закрывается внутри каждого метода.
    """

    @staticmethod
    def _get_service():
        """Получить экземпляр UserService через прямое инстанцирование."""
        from src.modules.users.repository import UserRepository, TelegramRepository
        from src.modules.users.service import UserService
        from src.bus.providers import get_message_bus

        return UserService(
            repository=UserRepository(),
            telegram_repository=TelegramRepository(),
            message_bus=get_message_bus(),
        )

    async def resolve_email_by_auth_id(
        self,
        auth_id: uuid.UUID,
    ) -> str | None:
        """
        Резолвить email по auth_id через прямой вызов сервиса.

        Args:
            auth_id: Идентификатор пользователя из модуля auth.

        Returns:
            Email пользователя или None, если не найден.

        Raises:
            Исключения пробрасываются наверх (NotFoundError, SQLAlchemyError и т.д.).
        """
        service = self._get_service()
        async for session in get_session():
            profile = await service.get_profile(session, auth_id)
            return getattr(profile, "email", None) if profile else None

    async def get_profile(self, auth_id: uuid.UUID):
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
        async for session in get_session():
            return await service.get_profile(session, auth_id)

    async def create_profile(
        self,
        auth_id: uuid.UUID,
        first_name: str | None = None,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        Создать профиль пользователя.

        Args:
            auth_id: Идентификатор пользователя.
            first_name: Имя.
            session: Опциональная сессия.

        Returns:
            True если создан.

        Raises:
            Исключения пробрасываются наверх (ConflictError, NotFoundError, SQLAlchemyError и т.д.).
        """
        service = self._get_service()
        if session is not None:
            await service.create_user_profile(
                session, auth_id, {"first_name": first_name}
            )
            return True

        async for s in get_session():
            await service.create_user_profile(s, auth_id, {"first_name": first_name})
            return True
