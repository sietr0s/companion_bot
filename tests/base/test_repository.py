"""
Тесты базового репозитория.

Проверяем CRUD-операции через конкретную модель (AuthAccount).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.repository import AuthRepository
from src.modules.users.repository import UserRepository


@pytest.fixture
def repo() -> AuthRepository:
    return AuthRepository()


class TestBaseRepository:
    """Тесты CRUD-операций BaseRepository через AuthRepository."""

    async def test_create(self, db_session: AsyncSession, repo: AuthRepository):
        """Создание сущности через словарь."""
        account = await repo.create(
            db_session,
            {
                "identifier": "create@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        assert account.id is not None
        assert account.identifier == "create@test.com"
        assert account.identifier_type == "email"
        assert account.created_at is not None

    async def test_create_from_pydantic(self, db_session: AsyncSession, repo: AuthRepository):
        """Создание сущности через Pydantic-модель."""
        from src.modules.users.schemas.public import UserCreate

        # Сначала создаём AuthAccount для ForeignKey
        auth_repo = AuthRepository()
        auth_account = await auth_repo.create(
            db_session,
            {
                "identifier": "pydantic_fk@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )

        # UserCreate — Pydantic-модель без auth_id (он пробрасывается отдельно)
        user_repo = UserRepository()
        data = UserCreate(first_name="Тест", last_name="Тестов")
        profile = await user_repo.create(
            db_session,
            {
                "auth_id": auth_account.id,
                **data.model_dump(exclude_unset=True),
            },
        )
        assert profile.first_name == "Тест"

    async def test_get_by_id(self, db_session: AsyncSession, repo: AuthRepository):
        """Получение сущности по ID."""
        account = await repo.create(
            db_session,
            {
                "identifier": "getbyid@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        found = await repo.get_by_id(db_session, account.id)
        assert found is not None
        assert found.identifier == "getbyid@test.com"

    async def test_get_by_id_not_found(self, db_session: AsyncSession, repo: AuthRepository):
        """Возврат None при поиске несуществующего ID."""
        found = await repo.get_by_id(db_session, uuid.uuid4())
        assert found is None

    async def test_get_all(self, db_session: AsyncSession, repo: AuthRepository):
        """Получение списка сущностей с пагинацией."""
        for i in range(5):
            await repo.create(
                db_session,
                {
                    "identifier": f"all{i}@test.com",
                    "identifier_type": "email",
                    "hashed_password": "hashed",
                },
            )
        results = await repo.get_all(db_session, skip=0, limit=3)
        assert len(results) == 3

    async def test_update(self, db_session: AsyncSession, repo: AuthRepository):
        """Обновление полей сущности."""
        account = await repo.create(
            db_session,
            {
                "identifier": "update@test.com",
                "identifier_type": "email",
                "hashed_password": "old_hash",
            },
        )
        updated = await repo.update(
            db_session,
            account,
            {
                "hashed_password": "new_hash",
            },
        )
        assert updated.hashed_password == "new_hash"
        assert updated.identifier == "update@test.com"  # Неизменённое поле

    async def test_delete(self, db_session: AsyncSession, repo: AuthRepository):
        """Удаление сущности."""
        account = await repo.create(
            db_session,
            {
                "identifier": "delete@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        await repo.delete(db_session, account)
        found = await repo.get_by_id(db_session, account.id)
        assert found is None
