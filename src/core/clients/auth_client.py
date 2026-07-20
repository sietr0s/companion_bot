"""
Клиент для прямого вызова сервиса авторизации.

Использует AuthService напрямую (без FastAPI Depends).
Session создаётся и закрывается внутри каждого метода.
"""

import logging
import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AuthClient:
    """
    Клиент для вызова методов AuthService напрямую.

    Принимает опциональный экземпляр AuthService.
    Если не передан — создаёт через прямое инстанцирование (без Depends).
    Session создаётся и закрывается внутри каждого метода.
    """

    def __init__(self, service=None):
        self._service = service

    def _get_service(self):
        """Получить экземпляр AuthService."""
        if self._service is not None:
            return self._service
        from src.bus import get_producer
        from src.modules.auth.repository import AuthRepository
        from src.modules.auth.service import AuthService

        return AuthService(repository=AuthRepository(), message_bus=get_producer())

    async def register(
        self,
        identifier: str,
        identifier_type: str = "telegram",
        password: str | None = None,
        session: AsyncSession | None = None,
    ) -> uuid.UUID:
        """
        Зарегистрировать нового пользователя через прямой вызов сервиса.

        Args:
            identifier: Уникальный идентификатор (chat_id).
            identifier_type: Тип идентификатора (telegram).
            password: Опциональный пароль. Если None — авто-генерация.
            session: Опциональная сессия. Если None — создаётся новая.

        Returns:
            ID созданной учётной записи.

        Raises:
            Исключения пробрасываются наверх (NotFoundError, ConflictError и т.д.).
        """
        service = self._get_service()
        # Генерируем надёжный пароль, если не передан
        if password is None:
            password = secrets.token_urlsafe(32)
        data: dict = {
            "identifier": identifier,
            "identifier_type": identifier_type,
            "password": password,
        }

        if session is not None:
            auth_id = await service.register_and_return_id(session, data)
            return auth_id

        from src.core.database import create_async_session

        async with create_async_session() as s:
            auth_id = await service.register_and_return_id(s, data)
            return auth_id

    async def get_by_identifier(
        self,
        identifier: str,
        session: AsyncSession | None = None,
    ) -> uuid.UUID | None:
        """
        Найти учётную запись по идентификатору.

        Args:
            identifier: Идентификатор (chat_id).
            session: Опциональная сессия.

        Returns:
            ID учётной записи или None, если не найдена.
        """
        service = self._get_service()
        if session is not None:
            account = await service.repository.get_by_identifier(session, identifier)
            return account.id if account else None

        from src.core.database import create_async_session

        async with create_async_session() as s:
            account = await service.repository.get_by_identifier(s, identifier)
            return account.id if account else None

    async def delete_account(
        self,
        auth_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Удалить учётную запись через API модуля auth."""
        service = self._get_service()
        if session is not None:
            await service.delete_account_internal(session, auth_id)
            return

        from src.core.database import create_async_session

        async with create_async_session() as own_session:
            await service.delete_account_internal(own_session, auth_id)
