"""
Интеграционные тесты настроек Telegram-аккаунта.

Проверяют CRUD операции с настройками через internal и public API.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_db_session
from src.main import app


@pytest_asyncio.fixture
async def test_client_with_db() -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP клиент с тестовой БД.
    Переопределяет get_db_session для использования test.db.
    """
    from tests.conftest import TestSessionLocal, test_engine

    # Создаём таблицы
    async with test_engine.begin() as conn:
        from src.base.model import Base

        await conn.run_sync(Base.metadata.create_all)

    # Генератор сессий
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    # Переопределяем зависимость get_db_session
    app.dependency_overrides[get_db_session] = override_get_db_session

    # Создаём клиент
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Очищаем
    app.dependency_overrides.clear()

    # Удаляем таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestTelegramSettingsInternalAPI:
    """Тесты internal API настроек Telegram."""

    @pytest.mark.asyncio
    async def test_create_settings_internal(self, test_client_with_db: AsyncClient):
        """Создание настроек через internal API."""
        client = test_client_with_db

        # Создаём Auth аккаунт
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "settings-test@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        # Создаём Telegram аккаунт через БД напрямую
        from src.modules.telegram_clients.models import TelegramAccount
        from tests.conftest import TestSessionLocal

        account_id = uuid.uuid4()
        async with TestSessionLocal() as session:
            tg_account = TelegramAccount(
                id=account_id,
                auth_id=uuid.UUID(auth_id),  # Преобразуем строку в UUID
                phone="+79991234567",
                session_file="/tmp/test_session",
                is_connected=True,
            )
            session.add(tg_account)
            await session.commit()

        # Создаём настройки
        settings_data = {
            "read_groups": False,
            "read_personal": True,
            "read_channels": False,
            "whitelist_chat_ids": [123456, 789012],
        }
        create_resp = await client.post(
            f"/internal/telegram/{account_id}/settings", json=settings_data
        )

        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["read_groups"] is False
        assert data["read_personal"] is True
        assert data["read_channels"] is False
        assert data["whitelist_chat_ids"] == [123456, 789012]

        # Очистка
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_get_settings_internal(self, test_client_with_db: AsyncClient):
        """Получение настроек через internal API."""
        client = test_client_with_db

        # Создаём Auth аккаунт
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "get-settings-test@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        # Создаём Telegram аккаунт через БД
        from src.modules.telegram_clients.models import TelegramAccount
        from tests.conftest import TestSessionLocal

        account_id = uuid.uuid4()
        async with TestSessionLocal() as session:
            tg_account = TelegramAccount(
                id=account_id,
                auth_id=uuid.UUID(auth_id),  # Преобразуем строку в UUID
                phone="+79997654321",
                session_file="/tmp/test_session2",
                is_connected=True,
            )
            session.add(tg_account)
            await session.commit()

        # Создаём настройки по умолчанию
        create_resp = await client.post(f"/internal/telegram/{account_id}/settings", json={})
        assert create_resp.status_code == 201

        # Получаем настройки
        get_resp = await client.get(f"/internal/telegram/{account_id}/settings")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["read_groups"] is True  # default
        assert data["read_personal"] is True  # default
        assert data["read_channels"] is True  # default

        # Очистка
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_update_settings_internal(self, test_client_with_db: AsyncClient):
        """Обновление настроек через internal API."""
        client = test_client_with_db

        # Создаём Auth аккаунт
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "update-settings-test@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        # Создаём Telegram аккаунт через БД
        from src.modules.telegram_clients.models import TelegramAccount
        from tests.conftest import TestSessionLocal

        account_id = uuid.uuid4()
        async with TestSessionLocal() as session:
            tg_account = TelegramAccount(
                id=account_id,
                auth_id=uuid.UUID(auth_id),  # Преобразуем строку в UUID
                phone="+79991112233",
                session_file="/tmp/test_session3",
                is_connected=True,
            )
            session.add(tg_account)
            await session.commit()

        # Создаём начальные настройки
        await client.post(
            f"/internal/telegram/{account_id}/settings",
            json={"read_groups": True, "read_personal": True, "read_channels": True},
        )

        # Обновляем настройки
        update_data = {"read_groups": False, "whitelist_chat_ids": [999888]}
        update_resp = await client.put(
            f"/internal/telegram/{account_id}/settings", json=update_data
        )

        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["read_groups"] is False
        assert data["whitelist_chat_ids"] == [999888]
        # Остальные поля должны сохраниться
        assert data["read_personal"] is True

        # Очистка
        await client.delete(f"/internal/auth/{auth_id}")


class TestTelegramSettingsPublicAPI:
    """Тесты public API настроек Telegram (с JWT аутентификацией)."""

    @pytest.mark.asyncio
    async def test_get_settings_public_requires_auth(self, test_client_with_db: AsyncClient):
        """Public API требует JWT аутентификации."""
        client = test_client_with_db

        # Пытаемся получить настройки без токена
        fake_account_id = uuid.uuid4()
        resp = await client.get(f"/public/telegram/{fake_account_id}/settings")

        # Должен вернуть 401 Unauthorized
        assert resp.status_code == 401
