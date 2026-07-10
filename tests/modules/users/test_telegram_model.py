"""
Тесты модели Telegram.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.models import Telegram, User


@pytest.fixture
async def telegram_data() -> dict:
    """Тестовые данные для Telegram."""
    return {
        "telegram_id": "123456789",
        "telegram_username": "testuser",
        "telegram_first_name": "Test",
        "telegram_last_name": "User",
    }


@pytest.fixture
async def existing_user_profile(db_session: AsyncSession) -> User:
    """Создаёт User для тестов."""
    profile = User(
        auth_id=uuid.uuid4(),
        first_name="Иван",
        last_name="Иванов",
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


class TestTelegramModel:
    """Тесты модели Telegram."""

    async def test_create_telegram(self, db_session: AsyncSession, telegram_data: dict):
        """Создание Telegram-аккаунта."""
        telegram = Telegram(**telegram_data)
        db_session.add(telegram)
        await db_session.commit()
        await db_session.refresh(telegram)

        assert telegram.id is not None
        assert telegram.telegram_id == "123456789"
        assert telegram.telegram_username == "testuser"
        assert telegram.telegram_first_name == "Test"
        assert telegram.telegram_last_name == "User"

    async def test_telegram_unique_telegram_id(self, db_session: AsyncSession, telegram_data: dict):
        """telegram_id должен быть уникальным."""
        telegram1 = Telegram(**telegram_data)
        db_session.add(telegram1)
        await db_session.commit()

        telegram2 = Telegram(**telegram_data)
        db_session.add(telegram2)

        with pytest.raises(Exception):
            await db_session.commit()

    async def test_telegram_optional_fields(self, db_session: AsyncSession):
        """Поля username, first_name, last_name могут быть NULL."""
        telegram = Telegram(telegram_id="987654321")
        db_session.add(telegram)
        await db_session.commit()
        await db_session.refresh(telegram)

        assert telegram.telegram_username is None
        assert telegram.telegram_first_name is None
        assert telegram.telegram_last_name is None

    async def test_telegram_relationship_with_user(
        self, db_session: AsyncSession, telegram_data: dict, existing_user_profile: User
    ):
        """Связь Telegram один-к-одному с User."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        telegram = Telegram(**telegram_data)
        db_session.add(telegram)
        await db_session.flush()  # Получаем ID до коммита

        # Устанавливаем связь - объект уже в сессии, просто меняем атрибут
        existing_user_profile.telegram_id = telegram.id

        await db_session.commit()

        # Проверяем связь с обеих сторон через явный запрос с подгрузкой relationship
        result = await db_session.execute(
            select(User)
            .options(selectinload(User.telegram))
            .where(User.id == existing_user_profile.id)
        )
        user_with_telegram = result.unique().scalar_one()

        result = await db_session.execute(
            select(Telegram).options(selectinload(Telegram.user)).where(Telegram.id == telegram.id)
        )
        telegram_with_user = result.unique().scalar_one()

        assert user_with_telegram.telegram is not None
        assert user_with_telegram.telegram.id == telegram.id
        assert telegram_with_user.user is not None
        assert telegram_with_user.user.id == existing_user_profile.id

    async def test_user_without_telegram(
        self, db_session: AsyncSession, existing_user_profile: User
    ):
        """User может существовать без Telegram."""
        await db_session.refresh(existing_user_profile)
        assert existing_user_profile.telegram is None

    async def test_get_telegram_by_telegram_id(self, db_session: AsyncSession, telegram_data: dict):
        """Получение Telegram по telegram_id."""
        telegram = Telegram(**telegram_data)
        db_session.add(telegram)
        await db_session.commit()

        result = await db_session.execute(
            select(Telegram).where(Telegram.telegram_id == "123456789")
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.id == telegram.id
