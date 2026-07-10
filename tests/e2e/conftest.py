"""
E2E тесты ms_starter — фикстуры.

Использует реальный Telegram API (Telethon + aiogram).
Session-файл: 1 на все тесты (scope="session").
БД: PostgreSQL с автооткатом после каждого теста.
"""
import os
import asyncio
import pytest
import pytest_asyncio
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

import httpx
from telethon import TelegramClient
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.main import app
from src.bus.in_memory import InMemoryProducer


# =============================================================================
# Константы
# =============================================================================

E2E_SESSION_DIR = Path(os.getenv("TG_TEST_SESSION_PATH", "/tmp/ms_starter_e2e_tests"))
E2E_SESSION_DIR.mkdir(parents=True, exist_ok=True)

TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_TEST_USER_PHONE = os.getenv("TG_TEST_USER_PHONE", "")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ms_starter_e2e"
)


# =============================================================================
# Telegram Client (Telethon) — фикстура уровня сессии
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Создать event loop для сессии."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def telegram_client() -> TelegramClient:
    """
    Telethon клиент для E2E тестов.
    
    Session-файл хранится между запусками.
    При первом запуске требует аутентификации (SMS-код + 2FA).
    """
    session_path = E2E_SESSION_DIR / "test_e2e"
    
    client = TelegramClient(
        str(session_path),
        TG_API_ID,
        TG_API_HASH,
        system_version="E2E Tests",
    )
    
    await client.connect()
    
    if not await client.is_user_authorized():
        if not TG_TEST_USER_PHONE:
            raise ValueError(
                "TG_TEST_USER_PHONE не указан. "
                "Установите переменную окружения или удалите session-файл для интерактивной аутентификации."
            )
        
        await client.send_code_request(TG_TEST_USER_PHONE)
        
        # Запрос кода через input (для интерактивного режима)
        code = input("Введите SMS-код из Telegram: ")
        await client.sign_in(TG_TEST_USER_PHONE, code)
    
    return client


# =============================================================================
# Telegram Bot (aiogram) — фикстура уровня сессии
# =============================================================================

@pytest.fixture(scope="session")
async def test_bot() -> Bot:
    """
    aiogram Bot для E2E тестов.
    
    Один бот на все тесты.
    """
    if not TG_BOT_TOKEN:
        raise ValueError("TG_BOT_TOKEN не указан. Установите переменную окружения.")
    
    bot = Bot(token=TG_BOT_TOKEN)
    
    # Проверка подключения
    info = await bot.get_me()
    print(f"Бот запущен: @{info.username}")
    
    return bot


# =============================================================================
# База данных (PostgreSQL) — фикстура уровня теста
# =============================================================================

@pytest_asyncio.fixture
async def e2e_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    AsyncSession для E2E тестов.
    
    PostgreSQL с автооткатом после каждого теста.
    """
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session_maker() as session:
        try:
            yield session
            # Коммит если тест прошёл успешно
            await session.commit()
        except Exception:
            # Rollback при ошибке теста
            await session.rollback()
            raise
        finally:
            await session.close()
    
    await engine.dispose()


# =============================================================================
# Шина сообщений (InMemoryProducer) — фикстура уровня теста
# =============================================================================

@pytest_asyncio.fixture
async def message_bus_collector() -> AsyncGenerator[InMemoryProducer, None]:
    """
    InMemoryProducer для сбора событий шины.
    
    Позволяет проверять опубликованные события в тестах.
    """
    bus = InMemoryProducer()
    yield bus


# =============================================================================
# HTTP-клиент (httpx) — фикстура уровня теста
# =============================================================================

@pytest_asyncio.fixture
async def e2e_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    httpx AsyncClient для вызовов API.
    
    Использует ASGITransport для прямого вызова FastAPI app.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# =============================================================================
# JWT токен — фикстура уровня теста
# =============================================================================

@pytest_asyncio.fixture
async def auth_token() -> str:
    """
    JWT токен для тестового пользователя.
    
    Создаёт токен без реальной регистрации (для скорости).
    """
    from src.core.security import create_access_token
    
    auth_id = uuid4()
    token = create_access_token(str(auth_id))
    
    return token
