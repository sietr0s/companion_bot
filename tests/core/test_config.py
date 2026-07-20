"""
Тесты конфигурации приложения.
"""

from src.core.config import Settings, settings


class TestConfig:
    """Тесты загрузки и дефолтов настроек."""

    def test_settings_instance_exists(self):
        """Глобальный экземпляр настроек создан."""
        assert settings is not None

    def test_default_values(self):
        """Дефолтные значения корректны."""
        s = Settings(
            JWT_SECRET_KEY="test",
            INTERNAL_SERVICE_KEY="internal-test-key",
            DATABASE_URL="sqlite+aiosqlite:///test.db",
        )
        assert s.JWT_ALGORITHM == "HS256"
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 15
        assert s.MESSAGE_BUS == "in_memory"
        assert s.DATABASE_POOL_SIZE == 5
        assert s.DEBUG is False

    def test_env_override(self):
        """Переменные окружения переопределяют дефолты."""
        import os

        os.environ["DEBUG"] = "true"
        os.environ["MESSAGE_BUS"] = "kafka"
        try:
            s = Settings(
                JWT_SECRET_KEY="test",
                INTERNAL_SERVICE_KEY="internal-test-key",
                DATABASE_URL="sqlite+aiosqlite:///test.db",
            )
            assert s.DEBUG is True
            assert s.MESSAGE_BUS == "kafka"
        finally:
            del os.environ["DEBUG"]
            del os.environ["MESSAGE_BUS"]
