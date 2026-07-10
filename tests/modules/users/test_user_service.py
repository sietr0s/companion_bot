"""
Тесты модуля пользователей: сервис и репозиторий.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.auth.repository import AuthRepository
from src.modules.telegram_clients.repository import TelegramAccountRepository
from src.modules.users.repository import UserRepository
from src.modules.users.service import UserService
from tests.conftest import MockBus


@pytest.fixture
async def existing_auth_id(db_session: AsyncSession) -> uuid.UUID:
    """Создаёт AuthAccount и возвращает его ID для тестов."""
    repo = AuthRepository()
    account = await repo.create(
        db_session,
        {
            "identifier": "user_test@test.com",
            "identifier_type": "email",
            "hashed_password": "hashed",
        },
    )
    return account.id


class TestUserRepository:
    """Тесты репозитория пользователей."""

    async def test_get_by_auth_id_found(
        self, db_session: AsyncSession, existing_auth_id: uuid.UUID
    ):
        repo = UserRepository()
        await repo.create(db_session, {"auth_id": existing_auth_id})

        found = await repo.get_by_auth_id(db_session, existing_auth_id)
        assert found is not None
        assert found.auth_id == existing_auth_id

    async def test_get_by_auth_id_not_found(self, db_session: AsyncSession):
        repo = UserRepository()
        found = await repo.get_by_auth_id(db_session, uuid.uuid4())
        assert found is None


class TestUserService:
    """Тесты сервиса пользователей."""

    async def test_create_user_profile(
        self,
        db_session: AsyncSession,
        user_service: UserService,
        existing_auth_id: uuid.UUID,
    ):
        """Успешное создание профиля."""
        data = {"first_name": "Иван", "last_name": "Иванов"}
        await user_service.create_user_profile(db_session, existing_auth_id, data)

        profile = await user_service.get_profile(db_session, existing_auth_id)
        assert profile.auth_id == existing_auth_id
        assert profile.first_name == "Иван"
        assert profile.last_name == "Иванов"

    async def test_create_user_profile_duplicate(
        self,
        db_session: AsyncSession,
        user_service: UserService,
        existing_auth_id: uuid.UUID,
    ):
        """Повторное создание профиля вызывает ConflictError."""
        data = {}
        await user_service.create_user_profile(db_session, existing_auth_id, data)

        with pytest.raises(ConflictError):
            await user_service.create_user_profile(db_session, existing_auth_id, data)

    async def test_get_profile_not_found(
        self,
        db_session: AsyncSession,
        user_service: UserService,
    ):
        """Получение несуществующего профиля вызывает NotFoundError."""
        with pytest.raises(NotFoundError):
            await user_service.get_profile(db_session, uuid.uuid4())

    async def test_update_profile(
        self,
        db_session: AsyncSession,
        user_service: UserService,
        existing_auth_id: uuid.UUID,
    ):
        """Обновление полей профиля."""
        # Создаём профиль
        data = {"first_name": "Старое"}
        await user_service.create_user_profile(db_session, existing_auth_id, data)

        # Обновляем
        update_data = {"first_name": "Новое", "bio": "Тестовая биография"}
        updated = await user_service.update_profile(db_session, existing_auth_id, update_data)
        assert updated.first_name == "Новое"
        assert updated.bio == "Тестовая биография"

    async def test_update_profile_publishes_event(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """При обновлении профиля публикуется событие profile.updated."""
        mock_bus = MockBus()
        service = UserService(
            repository=UserRepository(),
            telegram_repository=TelegramAccountRepository(),
            message_bus=mock_bus,
        )

        # Создаём профиль (публикуется profile.created)
        await service.create_user_profile(db_session, existing_auth_id, {})
        mock_bus.published.clear()

        # Обновляем
        update_data = {"first_name": "Новое"}
        await service.update_profile(db_session, existing_auth_id, update_data)

        assert len(mock_bus.published) == 1
        assert mock_bus.published[0][0] == "profile.updated"
        assert "first_name" in mock_bus.published[0][1]["fields_updated"]

    async def test_update_profile_no_changes_no_event(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """Если поля не изменились, событие не публикуется."""
        mock_bus = MockBus()
        service = UserService(
            repository=UserRepository(),
            telegram_repository=TelegramAccountRepository(),
            message_bus=mock_bus,
        )

        # Создаём с именем
        await service.create_user_profile(db_session, existing_auth_id, {"first_name": "Имя"})
        mock_bus.published.clear()

        # "Обновляем" тем же именем
        update_data = {"first_name": "Имя"}
        await service.update_profile(db_session, existing_auth_id, update_data)

        assert len(mock_bus.published) == 0

    async def test_create_profile_minimal(
        self,
        db_session: AsyncSession,
        user_service: UserService,
        existing_auth_id: uuid.UUID,
    ):
        """Создание профиля только с auth_id (без доп. полей)."""
        data = {}
        await user_service.create_user_profile(db_session, existing_auth_id, data)

        profile = await user_service.get_profile(db_session, existing_auth_id)
        assert profile.auth_id == existing_auth_id
        assert profile.first_name is None
        assert profile.last_name is None

    async def test_delete_profile(
        self,
        db_session: AsyncSession,
        user_service: UserService,
        existing_auth_id: uuid.UUID,
    ):
        """Удаление профиля пользователя."""
        data = {"first_name": "На удаление"}
        await user_service.create_user_profile(db_session, existing_auth_id, data)

        # Убеждаемся, что профиль существует
        profile = await user_service.get_profile(db_session, existing_auth_id)
        assert profile.first_name == "На удаление"

        # Удаляем
        await user_service.delete_profile(db_session, existing_auth_id)

        # Проверяем, что профиль больше не найден
        with pytest.raises(NotFoundError):
            await user_service.get_profile(db_session, existing_auth_id)

    async def test_create_profile_publishes_event(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """При создании профиля публикуется событие profile.created."""
        mock_bus = MockBus()
        service = UserService(
            repository=UserRepository(),
            telegram_repository=TelegramAccountRepository(),
            message_bus=mock_bus,
        )
        data = {"first_name": "Тест"}
        await service.create_user_profile(db_session, existing_auth_id, data)

        assert len(mock_bus.published) == 1
        assert mock_bus.published[0][0] == "profile.created"
        assert mock_bus.published[0][1]["auth_id"] == str(existing_auth_id)

    async def test_delete_profile_publishes_event(
        self,
        db_session: AsyncSession,
        existing_auth_id: uuid.UUID,
    ):
        """При удалении профиля публикуется событие profile.deleted."""
        mock_bus = MockBus()
        service = UserService(
            repository=UserRepository(),
            telegram_repository=TelegramAccountRepository(),
            message_bus=mock_bus,
        )

        # Создаём профиль (публикуется profile.created)
        await service.create_user_profile(db_session, existing_auth_id, {})
        mock_bus.published.clear()

        # Удаляем
        await service.delete_profile(db_session, existing_auth_id)

        assert len(mock_bus.published) == 1
        assert mock_bus.published[0][0] == "profile.deleted"
        assert mock_bus.published[0][1]["auth_id"] == str(existing_auth_id)
