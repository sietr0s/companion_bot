"""
Централизованная конфигурация приложения.

Используем pydantic-settings для валидации и загрузки
переменных окружения. Единая точка входа для всех настроек —
избегаем разбросанных os.getenv() по коду.
"""

import logging
from urllib.parse import quote

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env или переменных окружения."""

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
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}"
            f":{quote(self.DB_PASSWORD, safe='')}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # JWT — обязательное поле, без дефолта
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    # Шина сообщений: "in_memory" или "kafka"
    MESSAGE_BUS: str = "in_memory"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_GROUP_ID: str = "modular-monolith"

    # Приложение
    APP_TITLE: str = "Modular Monolith"
    DEBUG: bool = False
    PORT: int = 8000

    # Создание таблиц при старте (для разработки)
    # В production использовать только Alembic миграции
    CREATE_TABLES_ON_STARTUP: bool = True

    # Internal API (межмодульное взаимодействие)
    INTERNAL_API_BASE_URL: str = "http://localhost:8000/internal"

    # Telegram (Telethon)
    TG_API_ID: int = 0
    TG_API_HASH: str = ""
    TG_SESSION_DIR: str = "sessions"
    TG_APP_VERSION: str = "modular_monolith"
    TG_DEVICE_MODEL: str = "ModularMonolith"
    TG_SYSTEM_VERSION: str = "4.16.30-vxCUSTOM"

    # Logging
    LOG_LEVEL: str = "INFO"

    # SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "App"

    # Шаблоны
    TEMPLATES_DIR: str = "templates"

    # Media
    MEDIA_STORAGE_PROVIDER: str = "local"  # "local" | "s3"
    MEDIA_STORAGE_PATH: str = "uploads"  # для LocalStorage
    MEDIA_MAX_SIZE_MB: int = 50  # лимит загрузки

    # Telegram Bot (aiogram)
    TG_BOT_TOKEN: str = ""
    TG_BOT_MODE: str = "polling"  # "polling" | "webhook"
    TG_BOT_WEBHOOK_SECRET: str = ""
    APP_URL: str = "http://localhost:8000"  # для webhook

    # Classifier (AI-классификация)
    CLASSIFIER_MODEL_NAME: str = "facebook/bart-large-mnli"
    CLASSIFIER_DEVICE: int = -1  # -1 = CPU, 0 = GPU

    # Admin (seed-пользователь) — обязательные поля, без дефолтов
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    ADMIN_FIRST_NAME: str = "Admin"
    ADMIN_LAST_NAME: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

# Глобальный экземпляр настроек — импортируется во всех модулях
settings = Settings()
