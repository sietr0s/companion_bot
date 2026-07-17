"""Фикстуры для тестов модуля notifications."""

import uuid

import pytest_asyncio
from sqlalchemy import text

from src.base.model import Base
from tests.conftest import test_engine


@pytest_asyncio.fixture(autouse=True)
async def create_all_tables():
    """Создаёт все таблицы для тестов notifications."""
    async with test_engine.begin() as conn:
        # Создаём все таблицы
        await conn.run_sync(Base.metadata.create_all)

        # Включаем foreign keys для SQLite
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    yield


@pytest_asyncio.fixture
def mock_users_client(monkeypatch):
    """Мок для UsersClient.resolve_email_by_auth_id."""
    from src.core.clients.users_client import UsersClient

    async def mock_resolve_email_by_auth_id(self, auth_id: uuid.UUID) -> str:
        return f"user{str(auth_id)[:8]}@test.com"

    monkeypatch.setattr(UsersClient, "resolve_email_by_auth_id", mock_resolve_email_by_auth_id)
    return mock_resolve_email_by_auth_id
