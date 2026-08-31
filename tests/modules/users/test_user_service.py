"""Тесты модуля users: собеседники Telegram."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.bus_topics import BusTopics
from src.modules.users.repository import UserRepository
from src.modules.users.service import UserService
from tests.conftest import MockBus


class TestUserRepository:
    async def test_get_by_telegram_id_found(self, db_session: AsyncSession):
        repo = UserRepository()
        await repo.create(db_session, {"telegram_id": 111, "first_name": "Ann"})
        found = await repo.get_by_telegram_id(db_session, 111)
        assert found is not None
        assert found.first_name == "Ann"

    async def test_get_by_telegram_id_not_found(self, db_session: AsyncSession):
        repo = UserRepository()
        assert await repo.get_by_telegram_id(db_session, 999) is None


class TestUserService:
    async def test_get_or_create_creates(
        self, db_session: AsyncSession, user_service: UserService
    ):
        user = await user_service.get_or_create_from_telegram(
            db_session,
            telegram_id=42,
            username="alice",
            first_name="Alice",
        )
        assert user.telegram_id == 42
        assert user.username == "alice"

    async def test_get_or_create_returns_existing(
        self, db_session: AsyncSession, user_service: UserService
    ):
        first = await user_service.get_or_create_from_telegram(
            db_session, telegram_id=42, first_name="Alice"
        )
        second = await user_service.get_or_create_from_telegram(
            db_session, telegram_id=42, first_name="Alice"
        )
        assert first.id == second.id

    async def test_get_or_create_updates_name(
        self, db_session: AsyncSession
    ):
        bus = MockBus()
        service = UserService(repository=UserRepository(), message_bus=bus)
        await service.get_or_create_from_telegram(db_session, telegram_id=7, first_name="Old")
        updated = await service.get_or_create_from_telegram(
            db_session, telegram_id=7, first_name="New"
        )
        assert updated.first_name == "New"
        topics = [item[0] for item in bus.published]
        assert BusTopics.USER_CREATED in topics
        assert BusTopics.USER_UPDATED in topics

    async def test_notes_via_update(self, db_session: AsyncSession, user_service: UserService):
        user = await user_service.get_or_create_from_telegram(db_session, telegram_id=5)
        updated = await user_service.update(db_session, user.id, {"notes": "говорит коротко"})
        assert updated.notes == "говорит коротко"
