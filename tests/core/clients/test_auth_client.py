"""
Тесты для AuthClient — клиента прямого вызова сервиса авторизации.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.clients.auth_client import AuthClient
from src.modules.auth.repository import AuthRepository


class TestAuthClient:
    """Тесты AuthClient — клиента для межмодульного вызова."""

    async def test_register_with_session(self, db_session: AsyncSession):
        """
        register() с переданной сессией создаёт Auth.
        """
        client = AuthClient()
        auth_id = await client.register(
            identifier="tg_test_register",
            identifier_type="telegram",
            password="testpass",
            session=db_session,
        )
        assert auth_id is not None
        assert isinstance(auth_id, uuid.UUID)

        repo = AuthRepository()
        account = await repo.get_by_identifier(db_session, "tg_test_register")
        assert account is not None
        assert account.identifier == "tg_test_register"

    async def test_register_returns_none_on_error(self, db_session: AsyncSession):
        """
        register() возвращает None при ошибке (дубликат).
        """
        repo = AuthRepository()
        await repo.create(
            db_session,
            {
                "identifier": "tg_duplicate",
                "identifier_type": "telegram",
                "hashed_password": "hashed",
            },
        )

        client = AuthClient()
        auth_id = await client.register(
            identifier="tg_duplicate",
            identifier_type="telegram",
            password="testpass",
            session=db_session,
        )
        assert auth_id is None

    async def test_get_by_identifier_found(self, db_session: AsyncSession):
        """
        get_by_identifier() находит существующую запись.
        """
        repo = AuthRepository()
        account = await repo.create(
            db_session,
            {
                "identifier": "tg_find_me",
                "identifier_type": "telegram",
                "hashed_password": "hashed",
            },
        )

        client = AuthClient()
        found_id = await client.get_by_identifier(
            identifier="tg_find_me",
            session=db_session,
        )
        assert found_id is not None
        assert found_id == account.id

    async def test_get_by_identifier_not_found(self, db_session: AsyncSession):
        """
        get_by_identifier() возвращает None для несуществующего.
        """
        client = AuthClient()
        found_id = await client.get_by_identifier(
            identifier="tg_nonexistent",
            session=db_session,
        )
        assert found_id is None
