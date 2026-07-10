"""
Интеграционные тесты модуля users.

Проверяют CRUD операции с профилями пользователей через реальное API.
"""

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


class TestUsersCRUD:
    """Интеграционные тесты CRUD операций с пользователями."""

    @pytest.mark.asyncio
    async def test_create_user_profile(self, test_client_with_db: AsyncClient):
        """Создание профиля пользователя через internal API."""
        client = test_client_with_db

        # Сначала создаём Auth аккаунт
        register_data = {
            "identifier": "user-crud@test.com",
            "identifier_type": "email",
            "hashed_password": "testpassword123",
        }
        register_resp = await client.post("/internal/auth/", json=register_data)
        assert register_resp.status_code == 201
        auth_data = register_resp.json()
        auth_id = auth_data["id"]

        # Создаём профиль
        profile_data = {
            "auth_id": auth_id,
            "first_name": "Иван",
            "last_name": "Иванов",
            "bio": "Тестовая биография",
        }
        profile_create_resp = await client.post("/internal/users/", json=profile_data)
        assert profile_create_resp.status_code == 201
        profile = profile_create_resp.json()
        assert profile["auth_id"] == auth_id
        assert profile["first_name"] == "Иван"
        assert profile["last_name"] == "Иванов"
        assert profile["bio"] == "Тестовая биография"

        # Очистка
        await client.delete(f"/internal/users/{profile['id']}")
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_get_profile_by_id(self, test_client_with_db: AsyncClient):
        """Получение профиля по ID."""
        client = test_client_with_db

        # Создаём Auth и профиль
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "get-by-id@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        profile_create_resp = await client.post(
            "/internal/users/",
            json={
                "auth_id": auth_id,
                "first_name": "Петр",
                "last_name": "Петров",
            },
        )
        profile_id = profile_create_resp.json()["id"]

        # Получаем профиль по ID
        get_resp = await client.get(f"/internal/users/{profile_id}")
        assert get_resp.status_code == 200
        profile = get_resp.json()
        assert profile["id"] == profile_id
        assert profile["first_name"] == "Петр"

        # Очистка
        await client.delete(f"/internal/users/{profile_id}")
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_update_profile(self, test_client_with_db: AsyncClient):
        """Обновление профиля пользователя."""
        client = test_client_with_db

        # Создаём Auth и профиль
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "update-test@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        profile_create_resp = await client.post(
            "/internal/users/",
            json={
                "auth_id": auth_id,
                "first_name": "Старое",
                "last_name": "Имя",
                "bio": "Старая биография",
            },
        )
        profile_id = profile_create_resp.json()["id"]

        # Обновляем профиль (PATCH)
        update_data = {
            "first_name": "Новое",
            "bio": "Новая биография",
        }
        update_resp = await client.patch(f"/internal/users/{profile_id}", json=update_data)
        assert update_resp.status_code == 200
        updated_profile = update_resp.json()
        assert updated_profile["first_name"] == "Новое"
        assert updated_profile["bio"] == "Новая биография"

        # Очистка
        await client.delete(f"/internal/users/{profile_id}")
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_delete_profile(self, test_client_with_db: AsyncClient):
        """Удаление профиля пользователя."""
        client = test_client_with_db

        # Создаём Auth и профиль
        register_resp = await client.post(
            "/internal/auth/",
            json={
                "identifier": "delete-test@test.com",
                "identifier_type": "email",
                "hashed_password": "testpassword123",
            },
        )
        auth_id = register_resp.json()["id"]

        profile_create_resp = await client.post(
            "/internal/users/",
            json={
                "auth_id": auth_id,
                "first_name": "Удалить",
                "last_name": "Профиль",
            },
        )
        profile_id = profile_create_resp.json()["id"]

        # Удаляем профиль
        delete_resp = await client.delete(f"/internal/users/{profile_id}")
        assert delete_resp.status_code == 204

        # Проверяем, что профиль удалён
        get_resp = await client.get(f"/internal/users/{profile_id}")
        assert get_resp.status_code == 404

        # Очистка Auth
        await client.delete(f"/internal/auth/{auth_id}")

    @pytest.mark.asyncio
    async def test_list_users_with_filters(self, test_client_with_db: AsyncClient):
        """Получение списка пользователей с фильтрацией."""
        client = test_client_with_db

        # Создаём несколько профилей
        auth_ids = []
        profile_ids = []

        for i in range(3):
            register_resp = await client.post(
                "/internal/auth/",
                json={
                    "identifier": f"filter-test-{i}@test.com",
                    "identifier_type": "email",
                    "hashed_password": "testpassword123",
                },
            )
            auth_id = register_resp.json()["id"]
            auth_ids.append(auth_id)

            profile_create_resp = await client.post(
                "/internal/users/",
                json={
                    "auth_id": auth_id,
                    "first_name": f"User{i}",
                    "last_name": "Test",
                },
            )
            profile_ids.append(profile_create_resp.json()["id"])

        # Получаем всех пользователей
        list_resp = await client.get("/internal/users/")
        assert list_resp.status_code == 200
        users = list_resp.json()
        assert len(users) >= 3

        # Очистка
        for profile_id in profile_ids:
            await client.delete(f"/internal/users/{profile_id}")
        for auth_id in auth_ids:
            await client.delete(f"/internal/auth/{auth_id}")
