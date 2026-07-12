"""
Клиент для прямого вызова сервиса авторизации.

Использует DI-фабрику для получения сервиса с общей шиной.
Session создаётся и закрывается внутри каждого метода.
"""

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


class AuthClient:
    """
    Клиент для вызова методов AuthService напрямую.

    Получает сервис через фабрику зависимостей (как MediaClient).
    Session создаётся и закрывается внутри каждого метода.
    """

    @staticmethod
    def _get_service():
        """Получить экземпляр AuthService через DI-фабрику."""
        from src.modules.auth.dependencies import get_auth_service

        return get_auth_service()

    async def register(
        self,
        identifier: str,
        identifier_type: str = "telegram",
        password: str | None = None,
        session: AsyncSession | None = None,
    ) -> uuid.UUID | None:
        """
        Зарегистрировать нового пользователя через прямой вызов сервиса.

        Args:
            identifier: Уникальный идентификатор (chat_id).
            identifier_type: Тип идентификатора (telegram).
            password: Опциональный пароль. Если None — авто-генерация.
            session: Опциональная сессия. Если None — создаётся новая.

        Returns:
            ID созданной учётной записи или None при ошибке.
        """
        try:
            service = self._get_service()
            data: dict = {
                "identifier": identifier,
                "identifier_type": identifier_type,
                "password": password or "",
            }

            if session is not None:
                auth_id = await service.register_and_return_id(session, data)
                return auth_id

            async for s in get_session():
                auth_id = await service.register_and_return_id(s, data)
                return auth_id
        except ConflictError as e:
            logger.warning("Пользователь уже существует: %s (%s)", identifier, e)
            return None
        except NotFoundError as e:
            logger.error("Ресурс не найден при регистрации %s: %s", identifier, e)
            return None
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при регистрации %s: %s", identifier, e)
            raise
        except (ValueError, TypeError) as e:
            logger.error("Ошибка валидации данных при регистрации %s: %s", identifier, e)
            return None
        except Exception as e:
            logger.exception("Неожиданная ошибка при регистрации %s: %s", identifier, e)
            return None

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
            ID учётной записи или None.
        """
        service = self._get_service()
        if session is not None:
            account = await service.repository.get_by_identifier(session, identifier)
            return account.id if account else None

        async for s in get_session():
            account = await service.repository.get_by_identifier(s, identifier)
            return account.id if account else None
