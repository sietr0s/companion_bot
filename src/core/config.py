"""
Централизованная конфигурация приложения.

Используем pydantic-settings для валидации и загрузки
переменных окружения. Единая точка входа для всех настроек —
избегаем разбросанных os.getenv() по коду.
"""

from urllib.parse import quote

from src.core.settings import EnvironmentSettings


class Settings(EnvironmentSettings):
    """Настройки приложения, загружаемые из .env или переменных окружения."""

    # Offline API development: isolated local data, no integration/AI workers.
    SAFE_MODE: bool = False
    SAFE_MODE_DATABASE_PATH: str = "safe-mode.db"

    # БД — собирается из компонентов
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "modular_monolith"
    DB_DRIVER: str = "postgresql+asyncpg"
    DATABASE_POOL_SIZE: int = 5

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802 — property имитирует поле Settings
        """Собирает полный URL для подключения к БД с URL-кодированием пароля."""
        if self.SAFE_MODE:
            return f"sqlite+aiosqlite:///{self.SAFE_MODE_DATABASE_PATH}"
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}"
            f":{quote(self.DB_PASSWORD, safe='')}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # JWT — обязательное поле, без дефолта
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Шина сообщений: "in_memory" или "kafka"
    MESSAGE_BUS: str = "in_memory"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_GROUP_ID: str = "modular-monolith"

    # Приложение
    APP_TITLE: str = "Modular Monolith"
    DEBUG: bool = False

    # Создание таблиц при старте (для разработки)
    # В production использовать только Alembic миграции
    CREATE_TABLES_ON_STARTUP: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Local model cache shared by embeddings and speech recognition.
    MODEL_CACHE_DIR: str = "models"

    # LangSmith tracing for LangChain calls
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "companion_bot"
    LANGSMITH_ENDPOINT: str = ""


# Bootstrap-настройки процесса; изменяемые параметры принадлежат module/config.
settings = Settings()
