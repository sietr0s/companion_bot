"""
Сервис пользователей.

Содержит бизнес-логику управления профилями.
Модуль users полностью изолирован от auth —
auth_id приходит из JWT-токена через зависимости FastAPI,
а не из схемы запроса.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import ConflictError, NotFoundError
from src.modules.users.constants import ERROR_MESSAGES
from src.modules.users.models import Telegram, User
from src.modules.users.repository import TelegramRepository, UserRepository
from src.modules.users.schemas.events import ProfileCreated, ProfileDeleted, ProfileUpdated


class UserService(BaseService[UserRepository, User]):
    """
    Сервис управления профилями пользователей.

    Не зависит от модуля auth — получает auth_id
    из JWT-токена через зависимости FastAPI.
    """

    def __init__(
        self,
        repository: UserRepository,
        telegram_repository: TelegramRepository,
        message_bus: MessageProducer,
    ) -> None:
        super().__init__(repository)
        self.telegram_repository = telegram_repository
        self.message_bus = message_bus

    async def create_user_profile(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        data: dict,
    ) -> User:
        """
        Создать профиль пользователя.

        auth_id пробрасывается из JWT-токена (не из схемы!).
        data содержит опциональные поля профиля (first_name и т.д.).
        """
        existing = await self.repository.get_by_auth_id(session, auth_id)
        if existing:
            raise ConflictError(detail=ERROR_MESSAGES["profile_already_exists"])

        # Объединяем auth_id из токена с данными из схемы
        data["auth_id"] = auth_id
        profile = await self.repository.create(session, data)

        # Публикуем событие о создании профиля
        event = ProfileCreated(auth_id=auth_id, profile_id=profile.id)
        await self.message_bus.publish(BusTopics.PROFILE_CREATED, event.to_bus_dict())
        return profile

    async def get_profile(self, session: AsyncSession, auth_id: uuid.UUID):
        """Получить профиль по auth_id. Raise NotFoundError если не найден."""
        profile = await self.repository.get_by_auth_id(session, auth_id)
        if not profile:
            raise NotFoundError(detail=ERROR_MESSAGES["profile_not_found"])
        return profile

    async def update_profile(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
        data: dict,
    ):
        """
        Обновить профиль пользователя.

        Определяет, какие поля реально изменились,
        и публикует событие ProfileUpdated с их списком.
        """
        profile = await self.get_profile(session, auth_id)

        # Определяем изменённые поля до обновления
        fields_updated = [field for field in data if getattr(profile, field, None) != data[field]]

        profile = await self.repository.update(session, profile, data)

        # Публикуем событие только если были реальные изменения
        if fields_updated:
            event = ProfileUpdated(
                auth_id=auth_id,
                profile_id=profile.id,
                fields_updated=fields_updated,
            )
            await self.message_bus.publish(BusTopics.PROFILE_UPDATED, event.to_bus_dict())

        return profile

    async def delete_profile(self, session: AsyncSession, auth_id: uuid.UUID) -> None:
        """Удалить профиль пользователя по auth_id."""
        profile = await self.get_profile(session, auth_id)

        # Публикуем событие об удалении профиля
        event = ProfileDeleted(auth_id=auth_id, profile_id=profile.id)
        await self.message_bus.publish(BusTopics.PROFILE_DELETED, event.to_bus_dict())

        await self.repository.delete(session, profile)

    async def get_users(
        self,
        session: AsyncSession,
        filters: list[Filter] | None = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = "-created_at",
    ) -> tuple[list[User], int]:
        """Получить список пользователей с фильтрацией и пагинацией."""
        return await self.repository.get_list(session, filters, skip, limit, order_by)

    async def create_telegram_profile(
        self,
        session: AsyncSession,
        profile_id: uuid.UUID,
        data: dict,
    ) -> Telegram:
        """
        Создать Telegram-профиль и связать с User.

        Args:
            session: сессия БД
            profile_id: ID профиля пользователя
            data: данные Telegram-профиля (telegram_id, telegram_username, ...)

        Returns:
            Созданный Telegram-аккаунт

        Raises:
            ConflictError: если telegram_id уже зарегистрирован
            NotFoundError: если User не найден
        """
        # Проверить, есть ли уже Telegram
        existing = await self.telegram_repository.get_by_telegram_id(session, data["telegram_id"])
        if existing:
            raise ConflictError(detail="Telegram-аккаунт уже привязан")

        # Найти User по profile_id
        profile = await self.repository.get_by_id(session, profile_id)
        if not profile:
            raise NotFoundError(detail="Профиль пользователя не найден")

        # Создать Telegram и связать через foreign key
        telegram = await self.telegram_repository.create(session, data)
        profile.telegram_id = telegram.id
        await self.repository.update(session, profile, {})

        return telegram

    async def get_profile_with_telegram(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
    ) -> tuple[User | None, Telegram | None]:
        """
        Получить профиль с подгруженным Telegram.

        Returns:
            Кортеж (User, Telegram | None)
        """
        profile = await self.repository.get_by_auth_id_with_telegram(session, auth_id)
        telegram = profile.telegram if profile else None
        return profile, telegram

    async def get_telegram_by_auth_id(
        self,
        session: AsyncSession,
        auth_id: uuid.UUID,
    ):
        """Получить Telegram профиль текущего пользователя."""
        profile = await self.repository.get_by_auth_id_with_telegram(session, auth_id)
        return profile.telegram if profile else None
