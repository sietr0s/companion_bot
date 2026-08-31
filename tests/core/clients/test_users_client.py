"""Тесты UsersClient."""

from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.bus import configure_bus
from src.core.clients.users_client import UsersClient
from src.modules.users.repository import UserRepository
from tests.conftest import MockBus


class TestUsersClient:
    async def test_get_or_create(self, db_session: AsyncSession):
        bus = MockBus()
        configure_bus(bus, MagicMock())
        client = UsersClient()
        user = await client.get_or_create(
            telegram_id=555,
            first_name="Ann",
            username="ann",
            session=db_session,
        )
        assert user.telegram_id == 555
        found = await UserRepository().get_by_telegram_id(db_session, 555)
        assert found is not None
        assert found.id == user.id

        same = await client.get_or_create(telegram_id=555, session=db_session)
        assert same.id == user.id
