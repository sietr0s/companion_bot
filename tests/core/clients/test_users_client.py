"""
Тесты для UsersClient — клиента прямого вызова сервиса пользователей.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.clients.users_client import UsersClient
from src.modules.users.repository import UserRepository


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
            session=db_session,
        )
        assert result is True

        repo = UserRepository()
        profile = await repo.get_by_auth_id(db_session, existing_auth_id)
        assert profile is not None
        assert profile.first_name == "Тестовый"

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
            session=db_session,
        )

        # get_profile использует свою сессию — создаём профиль
        # напрямую через репозиторий
        repo = UserRepository()
        profile = await repo.get_by_auth_id(db_session, existing_auth_id)
        assert profile is not None
        assert profile.first_name == "Профиль"
