"""
Тесты для UsersClient — клиента прямого вызова сервиса пользователей.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.clients.users_client import UsersClient
from src.modules.users.repository import TelegramRepository, UserRepository


class TestUsersClient:
    """Тесты UsersClient — клиента для межмодульного вызова."""

    async def test_create_profile_with_session(
        self, db_session: AsyncSession, existing_auth_id: uuid.UUID
    ):
        """
        create_profile() с переданной сессией создаёт профиль.
        """
        client = UsersClient()
        result = await client.create_profile(
            auth_id=existing_auth_id,
            first_name="Тестовый",
            last_name="Пользователь",
            telegram_id=123456,
            telegram_username="test_user",
            session=db_session,
        )
        assert result is True

        repo = UserRepository()
        profile = await repo.get_by_auth_id(db_session, existing_auth_id)
        assert profile is not None
        assert profile.first_name == "Тестовый"
        assert profile.last_name == "Пользователь"

        telegram = await TelegramRepository().get_by_auth_id(db_session, existing_auth_id)
        assert telegram is not None
        assert telegram.telegram_id == "123456"
        assert telegram.telegram_username == "test_user"
        assert telegram.telegram_first_name == "Тестовый"
        assert telegram.telegram_last_name == "Пользователь"
        assert (
            await client.resolve_telegram_id_by_auth_id(
                existing_auth_id,
                session=db_session,
            )
            == 123456
        )

    async def test_get_profile_with_session(
        self, db_session: AsyncSession, existing_auth_id: uuid.UUID
    ):
        """
        get_profile() возвращает профиль по auth_id.
        """
        # Сначала создаём профиль
        client = UsersClient()
        await client.create_profile(
            auth_id=existing_auth_id,
            first_name="Профиль",
            telegram_id=123457,
            session=db_session,
        )

        profile = await client.get_profile(existing_auth_id, session=db_session)
        assert profile is not None
        assert profile.first_name == "Профиль"
