"""
Клиент для прямого вызова сервиса пользователей.

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


class UsersClient:
    """
    Клиент для вызова методов UserService напрямую.

    Получает сервис через фабрику зависимостей (как MediaClient).
    Session создаётся и закрывается внутри каждого метода.
    """

    @staticmethod
    def _get_service():
        """Получить экземпляр UserService через DI-фабрику."""
        from src.modules.users.dependencies import get_user_service

        return get_user_service()

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
        """
        try:
            service = self._get_service()
            async for session in get_session():
                profile = await service.get_profile(session, auth_id)
                return getattr(profile, "email", None) if profile else None
        except NotFoundError:
            logger.warning("Профиль не найден для auth_id: %s", auth_id)
            return None
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при получении профиля %s: %s", auth_id, e)
            raise
        except Exception as e:
            logger.exception("Неожиданная ошибка при резолве email для auth_id %s: %s", auth_id, e)
            return None

    async def get_profile(self, auth_id: uuid.UUID):
        """
        Получить профиль пользователя по auth_id.

        Args:
            auth_id: Идентификатор пользователя из модуля auth.

        Returns:
            Объект профиля или None.
        """
        try:
            service = self._get_service()
            async for session in get_session():
                return await service.get_profile(session, auth_id)
        except NotFoundError:
            logger.warning("Профиль не найден для auth_id: %s", auth_id)
            return None
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при получении профиля %s: %s", auth_id, e)
            raise
        except Exception as e:
            logger.exception("Неожиданная ошибка при получении профиля для auth_id %s: %s", auth_id, e)
            return None

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
            True если создан, False при ошибке.
        """
        try:
            service = self._get_service()
            if session is not None:
                await service.create_user_profile(
                    session, auth_id, {"first_name": first_name}
                )
                return True

            async for s in get_session():
                await service.create_user_profile(s, auth_id, {"first_name": first_name})
                return True
        except ConflictError as e:
            logger.warning("Профиль уже существует для auth_id %s: %s", auth_id, e)
            return False
        except NotFoundError as e:
            logger.error("Ресурс не найден при создании профиля %s: %s", auth_id, e)
            return False
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при создании профиля %s: %s", auth_id, e)
            raise
        except (ValueError, TypeError) as e:
            logger.error("Ошибка валидации данных при создании профиля %s: %s", auth_id, e)
            return False
        except Exception as e:
            logger.exception("Неожиданная ошибка при создании профиля для auth_id %s: %s", auth_id, e)
            return False
