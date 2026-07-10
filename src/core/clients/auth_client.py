"""
Клиент для прямого вызова сервиса авторизации.

Использует DI для получения сервиса и вызывает методы напрямую,
без HTTP-запросов. Для межмодульного взаимодействия в модульном монолите.
"""

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus.in_memory.producer import InMemoryProducer
from src.core.database import get_session
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService

logger = logging.getLogger(__name__)


class AuthClient:
    """
    Клиент для вызова методов AuthService напрямую.

    Создаёт сервис напрямую (не через Depends), чтобы
    можно было вызывать из обработчиков шины.
    """

    def __init__(self, message_bus=None):
        """
        Args:
            message_bus: Опциональная шина сообщений. Если None — создаётся новая.
        """
        self._message_bus = message_bus
        self._auth_service = AuthService(
            repository=AuthRepository(),
            message_bus=message_bus or InMemoryProducer(),
        )

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
            data: dict = {
                "identifier": identifier,
                "identifier_type": identifier_type,
                "password": password or "",
            }

            if session is not None:
                auth_id = await self._auth_service.register_and_return_id(session, data)
                return auth_id

            async for s in get_session():
                auth_id = await self._auth_service.register_and_return_id(s, data)
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
        if session is not None:
            account = await self._auth_service.repository.get_by_identifier(session, identifier)
            return account.id if account else None

        async for s in get_session():
            account = await self._auth_service.repository.get_by_identifier(s, identifier)
            return account.id if account else None
