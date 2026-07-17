"""
Тесты для seed-функций инициализации данных при старте.

Проверяет создание admin-пользователя:
- При первом запуске создаётся admin с ролью admin
- При повторном запуске не создаёт дубликат
- Admin имеет правильные данные (email, роль)
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bus import get_producer
from src.core.seed import seed_admin
from src.modules.auth.models import Auth
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService


@pytest.mark.asyncio
async def test_seed_admin_creates_admin(db_session: AsyncSession):
    """При первом запуске seed_admin создаёт admin-пользователя."""
    await seed_admin(db_session)

    repo = AuthRepository()
    admin = await repo.get_by_identifier(db_session, "admin@example.com")

    assert admin is not None
    assert admin.role == "admin"
    assert admin.identifier_type == "email"


@pytest.mark.asyncio
async def test_seed_admin_idempotent(db_session: AsyncSession):
    """Повторный вызов seed_admin не создаёт дубликат."""

    # Первый вызов
    await seed_admin(db_session)

    repo = AuthRepository()
    admin = await repo.get_by_identifier(db_session, "admin@example.com")
    assert admin is not None
    assert admin.role == "admin"

    admin_id = admin.id

    # Второй вызов — не должен создать дубликат
    await seed_admin(db_session)

    # Проверяем, что admin всё ещё один
    stmt = select(func.count()).select_from(Auth).where(Auth.role == "admin")
    result = await db_session.execute(stmt)
    count = result.scalar()

    assert count == 1

    # ID не изменился
    same_admin = await repo.get_by_identifier(db_session, "admin@example.com")
    assert same_admin is not None
    assert same_admin.id == admin_id


@pytest.mark.asyncio
async def test_seed_admin_password_is_hashed(db_session: AsyncSession):
    """Пароль admin сохраняется в хэшированном виде (не plaintext)."""
    await seed_admin(db_session)

    repo = AuthRepository()
    admin = await repo.get_by_identifier(db_session, "admin@example.com")

    assert admin is not None
    assert admin.hashed_password != "admin123"
    assert admin.hashed_password.startswith("$2b$")  # bcrypt hash


@pytest.mark.asyncio
async def test_seed_admin_can_login(db_session: AsyncSession):
    """Admin может войти с указанным паролем."""
    await seed_admin(db_session)

    # Проверяем логин через AuthService
    service = AuthService(repository=AuthRepository(), message_bus=get_producer())
    response = await service.login(
        db_session,
        {"identifier": "admin@example.com", "password": "admin123"},
    )

    assert response.access_token is not None
    assert response.token_type == "bearer"
