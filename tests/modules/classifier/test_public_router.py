"""Тесты HTTP API модуля classifier."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestClassifierPublicRouter:
    """Тесты публичного роутера classifier."""

    @pytest.mark.asyncio
    async def test_get_categories_empty(self, client: AsyncClient, admin_token: str):
        """Получение пустого списка категорий."""
        response = await client.get(
            "/api/v1/public/classifier/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, admin_token: str):
        """Создание категории."""
        data = {
            "name": "IT Вакансии",
            "slug": "it_vacancies",
            "description": "Категория для IT вакансий",
            "is_active": True,
        }
        response = await client.post(
            "/api/v1/public/classifier/categories",
            json=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "IT Вакансии"
        assert result["slug"] == "it_vacancies"
        assert result["description"] == "Категория для IT вакансий"
        assert "id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_category_invalid_slug(self, client: AsyncClient, admin_token: str):
        """Создание категории с невалидным slug."""
        data = {
            "name": "Test",
            "slug": "Invalid-Slug!",  # Должен быть только a-z0-9_
            "description": "Test",
        }
        response = await client.post(
            "/api/v1/public/classifier/categories",
            json=data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_category_unauthorized(self, client: AsyncClient):
        """Создание категории без авторизации."""
        data = {
            "name": "Test",
            "slug": "test",
            "description": "Test",
        }
        response = await client.post(
            "/api/v1/public/classifier/categories",
            json=data,
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_category_user_not_admin(self, client: AsyncClient, auth_token: str):
        """Создание категории пользователем без прав админа."""
        data = {
            "name": "Test",
            "slug": "test",
            "description": "Test",
        }
        response = await client.post(
            "/api/v1/public/classifier/categories",
            json=data,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_categories_with_data(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Получение списка категорий с данными."""
        # Создаём категорию через сервис (напрямую через БД)
        from src.modules.classifier.repository import CategoryRepository

        repo = CategoryRepository()
        await repo.create(
            db_session,
            {
                "name": "Category 1",
                "slug": "category_1",
                "description": "Description 1",
                "is_active": True,
            },
        )
        await db_session.commit()

        response = await client.get(
            "/api/v1/public/classifier/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result) == 1
        assert result[0]["name"] == "Category 1"
        assert result[0]["slug"] == "category_1"

    @pytest.mark.asyncio
    async def test_update_category(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Обновление категории."""
        # Создаём категорию
        from src.modules.classifier.repository import CategoryRepository

        repo = CategoryRepository()
        await repo.create(
            db_session,
            {
                "name": "Old Name",
                "slug": "old_slug",
                "description": "Old description",
                "is_active": True,
            },
        )
        await db_session.commit()

        # Обновляем
        update_data = {
            "name": "New Name",
            "description": "New description",
        }
        response = await client.patch(
            "/api/v1/public/classifier/categories/old_slug",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "New Name"
        assert result["description"] == "New description"
        assert result["slug"] == "old_slug"

    @pytest.mark.asyncio
    async def test_update_category_not_found(self, client: AsyncClient, admin_token: str):
        """Обновление несуществующей категории."""
        update_data = {"name": "New Name"}
        response = await client.patch(
            "/api/v1/public/classifier/categories/nonexistent",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_category(
        self, client: AsyncClient, admin_token: str, db_session: AsyncSession
    ):
        """Удаление категории."""
        # Создаём категорию
        from src.modules.classifier.repository import CategoryRepository

        repo = CategoryRepository()
        await repo.create(
            db_session,
            {
                "name": "ToDelete",
                "slug": "to_delete",
                "description": "Will be deleted",
                "is_active": True,
            },
        )
        await db_session.commit()

        # Удаляем
        response = await client.delete(
            "/api/v1/public/classifier/categories/to_delete",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 204

        # Проверяем что удалена
        response = await client.get(
            "/api/v1/public/classifier/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, client: AsyncClient, admin_token: str):
        """Удаление несуществующей категории."""
        response = await client.delete(
            "/api/v1/public/classifier/categories/nonexistent",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404
