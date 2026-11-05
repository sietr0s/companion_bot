"""
Интеграционные тесты настроек Telegram-аккаунта.

Проверяют CRUD операции с настройками через manager и public API.
"""

import uuid

import pytest
from httpx import AsyncClient


class TestTelegramSettingsManagerAPI:
    """Тесты manager API настроек Telegram."""

    @pytest.mark.asyncio
    async def test_create_settings_manager(self, api_client: AsyncClient, admin_token: str):
        """Создание настроек через manager API."""
        client = api_client
        client.headers["Authorization"] = f"Bearer {admin_token}"

        # Создаём Auth аккаунт
        # Создаём Telegram аккаунт через БД напрямую
        from src.modules.telegram_clients.models import TelegramAccount
        from tests.conftest import TestSessionLocal

        account_id = uuid.uuid4()
        async with TestSessionLocal() as session:
            tg_account = TelegramAccount(
                id=account_id,
                phone="+79991234567",
                session_file="/tmp/test_session",
                is_connected=True,
            )
            session.add(tg_account)
            await session.commit()

        # Создаём настройки
        settings_data = {
            "use_whitelist": True,
            "whitelist_chat_ids": [123456, 789012],
        }
        create_resp = await client.post(
            f"/api/v1/public/telegram/{account_id}/settings", json=settings_data
        )

        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["use_whitelist"] is True
        assert data["whitelist_chat_ids"] == [123456, 789012]

        # Очистка

    @pytest.mark.asyncio
    async def test_get_settings_manager(self, api_client: AsyncClient, admin_token: str):
        """Получение настроек через manager API."""
        client = api_client
        client.headers["Authorization"] = f"Bearer {admin_token}"

        # Создаём Auth аккаунт
        # Создаём Telegram аккаунт через БД
        from src.modules.telegram_clients.models import TelegramAccount
        from tests.conftest import TestSessionLocal

        account_id = uuid.uuid4()
        async with TestSessionLocal() as session:
            tg_account = TelegramAccount(
                id=account_id,
                phone="+79997654321",
                session_file="/tmp/test_session2",
                is_connected=True,
            )
            session.add(tg_account)
            await session.commit()

        # Создаём настройки по умолчанию
        create_resp = await client.post(f"/api/v1/public/telegram/{account_id}/settings", json={})
        assert create_resp.status_code == 201

        # Получаем настройки
        get_resp = await client.get(f"/api/v1/public/telegram/{account_id}/settings")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["use_whitelist"] is True  # default

        # Очистка

    @pytest.mark.asyncio
    async def test_update_settings_manager(self, api_client: AsyncClient, admin_token: str):
        """Обновление настроек через manager API."""
        client = api_client
        client.headers["Authorization"] = f"Bearer {admin_token}"

        # Создаём Auth аккаунт
        # Создаём Telegram аккаунт через БД
        from src.modules.telegram_clients.models import TelegramAccount
        from tests.conftest import TestSessionLocal

        account_id = uuid.uuid4()
        async with TestSessionLocal() as session:
            tg_account = TelegramAccount(
                id=account_id,
                phone="+79991112233",
                session_file="/tmp/test_session3",
                is_connected=True,
            )
            session.add(tg_account)
            await session.commit()

        # Создаём начальные настройки
        await client.post(
            f"/api/v1/public/telegram/{account_id}/settings",
            json={"use_whitelist": True},
        )

        # Обновляем настройки
        update_data = {"use_whitelist": False, "whitelist_chat_ids": [999888]}
        update_resp = await client.put(
            f"/api/v1/public/telegram/{account_id}/settings", json=update_data
        )

        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["use_whitelist"] is False
        assert data["whitelist_chat_ids"] == [999888]
        # Остальные поля должны сохраниться

        # Очистка


class TestTelegramSettingsPublicAPI:
    """Тесты public API настроек Telegram (с JWT аутентификацией)."""

    @pytest.mark.asyncio
    async def test_get_settings_public_requires_auth(self, api_client: AsyncClient):
        """Public API требует JWT аутентификации."""
        client = api_client

        # Пытаемся получить настройки без токена
        fake_account_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/public/telegram/{fake_account_id}/settings")

        # Отказ до обращения к БД: без Bearer-токена менеджерские ручки недоступны.
        assert resp.status_code == 401
