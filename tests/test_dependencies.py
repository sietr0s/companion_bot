"""
Тесты DI-зависимостей.

Проверяет, что все фабрики корректно создают
экземпляры сервисов и репозиториев.
"""

from unittest.mock import MagicMock

from src.bus import configure_bus
from src.modules.auth.dependencies import get_auth_repository, get_auth_service
from src.modules.telegram_clients.dependencies import (
    get_telegram_account_repository,
    get_telegram_settings_repository,
)
from src.modules.users.dependencies import get_user_repository, get_user_service


class TestAuthDependencies:
    """Тесты DI-зависимостей модуля auth."""

    def test_get_auth_repository(self):
        """Репозиторий создаётся без параметров."""
        repo = get_auth_repository()
        assert repo is not None
        assert hasattr(repo, "model")

    def test_get_auth_service(self):
        """Сервис создаётся с репозиторием и шиной."""

        repo = get_auth_repository()
        bus = MagicMock()
        configure_bus(bus, MagicMock())
        service = get_auth_service(repo=repo)
        assert service is not None
        assert service.repository is repo
        assert service.message_bus is bus


class TestUserDependencies:
    """Тесты DI-зависимостей модуля users."""

    def test_get_user_repository(self):
        """Репозиторий пользователей создаётся без параметров."""
        repo = get_user_repository()
        assert repo is not None

    def test_get_user_service(self):
        """Сервис пользователей создаётся с репозиторием и шиной."""

        repo = get_user_repository()
        bus = MagicMock()
        configure_bus(bus, MagicMock())
        service = get_user_service(repo=repo)
        assert service is not None
        assert service.repository is repo
        assert service.message_bus is bus


class TestTelegramDependencies:
    """Тесты DI-зависимостей модуля telegram_clients."""

    def test_get_telegram_account_repository(self):
        """Репозиторий Telegram-аккаунтов создаётся без параметров."""
        repo = get_telegram_account_repository()
        assert repo is not None

    def test_get_telegram_settings_repository(self):
        """Репозиторий настроек Telegram создаётся без параметров."""
        repo = get_telegram_settings_repository()
        assert repo is not None
