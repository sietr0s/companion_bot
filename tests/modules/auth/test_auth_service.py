"""
Тесты модуля авторизации: сервис и репозиторий.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, UnauthorizedError
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService
from tests.conftest import MockBus


class TestAuthRepository:
    """Тесты репозитория авторизации."""

    async def test_get_by_identifier_email_found(
        self, db_session: AsyncSession, auth_repository: AuthRepository
    ):
        """Поиск существующего email."""
        await auth_repository.create(
            db_session,
            {
                "identifier": "find@test.com",
                "identifier_type": "email",
                "hashed_password": "hashed",
            },
        )
        found = await auth_repository.get_by_identifier(db_session, "find@test.com")
        assert found is not None
        assert found.identifier == "find@test.com"
        assert found.identifier_type == "email"

    async def test_get_by_identifier_phone_found(
        self, db_session: AsyncSession, auth_repository: AuthRepository
    ):
        """Поиск существующего телефона."""
        await auth_repository.create(
            db_session,
            {
                "identifier": "+79991234567",
                "identifier_type": "phone",
                "hashed_password": "hashed",
            },
        )
        found = await auth_repository.get_by_identifier(db_session, "+79991234567")
        assert found is not None
        assert found.identifier == "+79991234567"
        assert found.identifier_type == "phone"

    async def test_get_by_identifier_telegram_found(
        self, db_session: AsyncSession, auth_repository: AuthRepository
    ):
        """Поиск существующего telegram username."""
        await auth_repository.create(
            db_session,
            {
                "identifier": "@testuser",
                "identifier_type": "telegram",
                "hashed_password": "hashed",
            },
        )
        found = await auth_repository.get_by_identifier(db_session, "@testuser")
        assert found is not None
        assert found.identifier == "@testuser"
        assert found.identifier_type == "telegram"

    async def test_get_by_identifier_not_found(
        self, db_session: AsyncSession, auth_repository: AuthRepository
    ):
        """Поиск несуществующего identifier возвращает None."""
        found = await auth_repository.get_by_identifier(db_session, "missing@test.com")
        assert found is None


class TestAuthService:
    """Тесты сервиса авторизации."""

    async def test_register_email_success(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Успешная регистрация по email возвращает JWT-токен."""
        data = {
            "identifier": "new@test.com",
            "identifier_type": "email",
            "password": "securepass123",
        }
        result = await auth_service.register(db_session, data)
        assert result.access_token is not None
        assert result.token_type == "bearer"

    async def test_register_phone_success(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Успешная регистрация по телефону возвращает JWT-токен."""
        data = {
            "identifier": "+79991234567",
            "identifier_type": "phone",
            "password": "securepass123",
        }
        result = await auth_service.register(db_session, data)
        assert result.access_token is not None
        assert result.token_type == "bearer"

    async def test_register_telegram_success(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Успешная регистрация по telegram username возвращает JWT-токен."""
        data = {
            "identifier": "@testuser123",
            "identifier_type": "telegram",
            "password": "securepass123",
        }
        result = await auth_service.register(db_session, data)
        assert result.access_token is not None
        assert result.token_type == "bearer"

    async def test_register_duplicate_email(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Повторная регистрация с тем же email вызывает ConflictError."""
        data = {
            "identifier": "dup@test.com",
            "identifier_type": "email",
            "password": "securepass123",
        }
        await auth_service.register(db_session, data)

        with pytest.raises(ConflictError):
            await auth_service.register(db_session, data)

    async def test_register_duplicate_phone(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Повторная регистрация с тем же телефоном вызывает ConflictError."""
        data = {
            "identifier": "+79999999999",
            "identifier_type": "phone",
            "password": "securepass123",
        }
        await auth_service.register(db_session, data)

        with pytest.raises(ConflictError):
            await auth_service.register(db_session, data)

    async def test_register_duplicate_telegram(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Повторная регистрация с тем же telegram username вызывает ConflictError."""
        data = {
            "identifier": "@dupuser",
            "identifier_type": "telegram",
            "password": "securepass123",
        }
        await auth_service.register(db_session, data)

        with pytest.raises(ConflictError):
            await auth_service.register(db_session, data)

    async def test_register_publishes_event(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """При регистрации публикуется событие user.registered."""
        mock_bus = MockBus()
        service = AuthService(repository=AuthRepository(), message_bus=mock_bus)
        data = {
            "identifier": "event@test.com",
            "identifier_type": "email",
            "password": "securepass123",
        }
        await service.register(db_session, data)

        assert len(mock_bus.published) == 1
        assert mock_bus.published[0][0] == "auth.event.user.registered"
        assert mock_bus.published[0][1]["identifier"] == "event@test.com"
        assert mock_bus.published[0][1]["identifier_type"] == "email"

    async def test_login_email_success(self, db_session: AsyncSession, auth_service: AuthService):
        """Успешный вход по email возвращает JWT-токен."""
        # Сначала регистрируемся
        reg_data = {
            "identifier": "login@test.com",
            "identifier_type": "email",
            "password": "securepass123",
        }
        await auth_service.register(db_session, reg_data)

        # Затем входим
        login_data = {"identifier": "login@test.com", "password": "securepass123"}
        result = await auth_service.login(db_session, login_data)
        assert result.access_token is not None

    async def test_login_phone_success(self, db_session: AsyncSession, auth_service: AuthService):
        """Успешный вход по телефону возвращает JWT-токен."""
        # Сначала регистрируемся
        reg_data = {
            "identifier": "+79991112233",
            "identifier_type": "phone",
            "password": "securepass123",
        }
        await auth_service.register(db_session, reg_data)

        # Затем входим
        login_data = {"identifier": "+79991112233", "password": "securepass123"}
        result = await auth_service.login(db_session, login_data)
        assert result.access_token is not None

    async def test_login_telegram_success(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Успешный вход по telegram username возвращает JWT-токен."""
        # Сначала регистрируемся
        reg_data = {
            "identifier": "@loginuser",
            "identifier_type": "telegram",
            "password": "securepass123",
        }
        await auth_service.register(db_session, reg_data)

        # Затем входим
        login_data = {"identifier": "@loginuser", "password": "securepass123"}
        result = await auth_service.login(db_session, login_data)
        assert result.access_token is not None

    async def test_login_wrong_identifier(
        self, db_session: AsyncSession, auth_service: AuthService
    ):
        """Вход с несуществующим identifier вызывает UnauthorizedError."""
        login_data = {"identifier": "nobody@test.com", "password": "securepass123"}
        with pytest.raises(UnauthorizedError):
            await auth_service.login(db_session, login_data)

    async def test_login_wrong_password(self, db_session: AsyncSession, auth_service: AuthService):
        """Вход с неверным паролем вызывает UnauthorizedError."""
        reg_data = {
            "identifier": "wrongpw@test.com",
            "identifier_type": "email",
            "password": "securepass123",
        }
        await auth_service.register(db_session, reg_data)

        login_data = {"identifier": "wrongpw@test.com", "password": "wrongpassword"}
        with pytest.raises(UnauthorizedError):
            await auth_service.login(db_session, login_data)

    async def test_login_publishes_event(self, db_session: AsyncSession, auth_service: AuthService):
        """При входе публикуется событие user.logged_in."""
        mock_bus = MockBus()
        service = AuthService(repository=AuthRepository(), message_bus=mock_bus)

        # Регистрация
        reg_data = {
            "identifier": "logevent@test.com",
            "identifier_type": "email",
            "password": "securepass123",
        }
        await service.register(db_session, reg_data)

        # Вход
        login_data = {"identifier": "logevent@test.com", "password": "securepass123"}
        await service.login(db_session, login_data)

        # Второе событие — user.logged_in
        assert mock_bus.published[1][0] == "auth.event.user.logged_in"
        assert mock_bus.published[1][1]["identifier"] == "logevent@test.com"
        assert mock_bus.published[1][1]["identifier_type"] == "email"


class TestIdentifierValidation:
    """Тесты валидации identifier."""

    def test_valid_telegram_username_with_at(self):
        """Валидный telegram username с @."""
        from src.modules.auth.schemas.public.auth import RegisterRequest

        data = RegisterRequest(
            identifier="@validuser",
            identifier_type="telegram",
            password="securepass123",
        )
        assert data.identifier == "@validuser"

    def test_valid_telegram_username_without_at(self):
        """Валидный telegram username без @."""
        from src.modules.auth.schemas.public.auth import RegisterRequest

        data = RegisterRequest(
            identifier="validuser",
            identifier_type="telegram",
            password="securepass123",
        )
        assert data.identifier == "validuser"

    def test_valid_telegram_username_with_underscore(self):
        """Валидный telegram username с подчеркиванием."""
        from src.modules.auth.schemas.public.auth import RegisterRequest

        data = RegisterRequest(
            identifier="@user_name123",
            identifier_type="telegram",
            password="securepass123",
        )
        assert data.identifier == "@user_name123"

    def test_invalid_telegram_username_too_short(self):
        """Telegram username слишком короткий."""
        from src.modules.auth.schemas.public.auth import RegisterRequest

        with pytest.raises(ValueError) as exc_info:
            RegisterRequest(
                identifier="@abc",
                identifier_type="telegram",
                password="securepass123",
            )
        assert "от 5 до 32 символов" in str(exc_info.value)

    def test_invalid_telegram_username_starts_with_digit(self):
        """Telegram username начинается с цифры."""
        from src.modules.auth.schemas.public.auth import RegisterRequest

        with pytest.raises(ValueError) as exc_info:
            RegisterRequest(
                identifier="@123user",
                identifier_type="telegram",
                password="securepass123",
            )
        assert "не может начинаться с цифры" in str(exc_info.value)

    def test_invalid_telegram_username_special_chars(self):
        """Telegram username содержит недопустимые символы."""
        from src.modules.auth.schemas.public.auth import RegisterRequest

        with pytest.raises(ValueError) as exc_info:
            RegisterRequest(
                identifier="@user@name",
                identifier_type="telegram",
                password="securepass123",
            )
        assert "только буквы, цифры и подчеркивание" in str(exc_info.value)
