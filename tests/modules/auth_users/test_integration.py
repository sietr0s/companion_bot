"""
Интеграционные тесты модулей auth и users.

Проверяют полный цикл через реальное API: регистрация → создание профиля → получение профиля.
Используют тестовую SQLite БД и переопределение зависимостей.
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


class TestAuthUsersIntegration:
    """Интеграционные тесты auth + users через реальное API."""

    @pytest.mark.asyncio
    async def test_register_then_create_profile(self, test_client_with_db: AsyncClient):
        """Полный цикл: регистрация аккаунта → создание профиля → получение."""
        client = test_client_with_db

        # 1. Регистрация аккаунта (internal API)
        register_data = {
            "identifier": "integration@test.com",
            "identifier_type": "email",
            "hashed_password": "testpassword123",
        }
        register_resp = await client.post("/internal/auth/", json=register_data)
        assert register_resp.status_code == 201
        auth_data = register_resp.json()
        auth_id = uuid.UUID(auth_data["id"])

        # 2. Создание профиля (internal API)
        profile_data = {
            "auth_id": str(auth_id),
            "first_name": "Иван",
            "last_name": "Иванов",
        }
        profile_create_resp = await client.post("/internal/users/", json=profile_data)
        assert profile_create_resp.status_code == 201
        profile_data_resp = profile_create_resp.json()
        assert profile_data_resp["auth_id"] == str(auth_id)
        assert profile_data_resp["first_name"] == "Иван"
        assert profile_data_resp["last_name"] == "Иванов"

        # 3. Получение профиля по ID
        profile_get_resp = await client.get(f"/internal/users/{profile_data_resp['id']}")
        assert profile_get_resp.status_code == 200
        profile_get_data = profile_get_resp.json()
        assert profile_get_data["auth_id"] == str(auth_id)
        assert profile_get_data["first_name"] == "Иван"

        # 4. Очистка (удаление профиля и аккаунта)
        delete_resp = await client.delete(f"/internal/users/{profile_data_resp['id']}")
        assert delete_resp.status_code == 204

        delete_auth_resp = await client.delete(f"/internal/auth/{auth_id}")
        assert delete_auth_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_register_and_get_profile_by_auth_id(self, test_client_with_db: AsyncClient):
        """Регистрация → создание профиля → получение по auth_id через JWT."""
        client = test_client_with_db

        # 1. Регистрация
        register_data = {
            "identifier": "jwt-test@test.com",
            "identifier_type": "email",
            "hashed_password": "testpassword123",
        }
        register_resp = await client.post("/internal/auth/", json=register_data)
        assert register_resp.status_code == 201
        auth_data = register_resp.json()
        auth_id = uuid.UUID(auth_data["id"])

        # 2. Создаём профиль через internal API
        profile_data = {
            "auth_id": str(auth_id),
            "first_name": "Петр",
            "last_name": "Петров",
        }
        profile_resp = await client.post("/internal/users/", json=profile_data)
        assert profile_resp.status_code == 201
        profile_id = uuid.UUID(profile_resp.json()["id"])

        # 3. Получаем токен для этого пользователя
        from src.core.security import create_access_token

        token = create_access_token(str(auth_id), "user")

        # 4. Получаем свой профиль через публичное API с JWT
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/public/users/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["auth_id"] == str(auth_id)
        assert me_data["first_name"] == "Петр"

        # 5. Очистка
        delete_profile_resp = await client.delete(f"/internal/users/{profile_id}")
        assert delete_profile_resp.status_code == 204
        delete_auth_resp = await client.delete(f"/internal/auth/{auth_id}")
        assert delete_auth_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_register_duplicate_identifier(self, test_client_with_db: AsyncClient):
        """Попытка регистрации с дублирующимся email."""
        client = test_client_with_db

        # 1. Первая регистрация
        register_data = {
            "identifier": "duplicate@test.com",
            "identifier_type": "email",
            "hashed_password": "testpassword123",
        }
        register_resp = await client.post("/internal/auth/", json=register_data)
        assert register_resp.status_code == 201

        # 2. Вторая регистрация с тем же email должна вернуть ошибку
        register_data_2 = {
            "identifier": "duplicate@test.com",
            "identifier_type": "email",
            "hashed_password": "testpassword123",
        }
        register_resp_2 = await client.post("/internal/auth/", json=register_data_2)
        assert register_resp_2.status_code == 409  # Conflict

        # 3. Очистка
        auth_data = register_resp.json()
        auth_id_1 = uuid.UUID(auth_data["id"])
        delete_auth_resp = await client.delete(f"/internal/auth/{auth_id_1}")
        assert delete_auth_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_create_profile_for_nonexistent_auth(self, test_client_with_db: AsyncClient):
        """Попытка создать профиль для несуществующего auth_id."""
        client = test_client_with_db

        fake_auth_id = uuid.uuid4()
        profile_data = {
            "auth_id": str(fake_auth_id),
            "first_name": "Тест",
            "last_name": "Тестов",
        }
        profile_create_resp = await client.post("/internal/users/", json=profile_data)
        # Профиль создастся (foreign key не проверяется на уровне БД)
        # Но это ожидаемое поведение для modular monolith
        assert profile_create_resp.status_code == 201

        # Очистка
        created_profile_id = uuid.UUID(profile_create_resp.json()["id"])
        delete_resp = await client.delete(f"/internal/users/{created_profile_id}")
        assert delete_resp.status_code == 204
