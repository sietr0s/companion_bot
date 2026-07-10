"""
Общие фикстуры для тестов.

Асинхронная SQLite в памяти — быстрая изоляция для каждого теста.
Не требует поднятого PostgreSQL.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.base.model import Base
from src.bus.in_memory.producer import InMemoryProducer
from src.bus.interface import MessageBus
from src.core.security import create_access_token
from src.main import app
from src.modules.auth.models import Auth
from src.modules.auth.repository import AuthRepository
from src.modules.auth.service import AuthService
from src.modules.telegram_clients.repository import TelegramAccountRepository
from src.modules.users.repository import UserRepository
from src.modules.users.service import UserService

# SQLite в памяти для тестов — изолирована и быстра
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Создаём тестовый движок с поддержкой foreign keys
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest_asyncio.fixture(autouse=True)
async def enable_sqlite_foreign_keys():
    """Включает поддержку foreign keys для SQLite."""
    from sqlalchemy import text

    async with test_engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
    yield
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Единственный event loop на всю сессию тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    """
    Создаёт и удаляет таблицы для каждого теста.
    Обеспечивает чистую БД перед каждым тестом.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Фабрика тестовых сессий с автоматическим откатом."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
def message_bus() -> MessageBus:
    """In-memory шина для тестов — без внешних зависимостей."""
    return InMemoryProducer()


class MockBus:
    """Заглушка шины сообщений для тестов, собирающая опубликованные события."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, topic: str, message: dict) -> None:
        self.published.append((topic, message))


@pytest_asyncio.fixture
def auth_repository() -> AuthRepository:
    return AuthRepository()


@pytest_asyncio.fixture
def auth_service(auth_repository: AuthRepository, message_bus: MessageBus) -> AuthService:
    return AuthService(repository=auth_repository, message_bus=message_bus)


@pytest_asyncio.fixture
def user_repository() -> UserRepository:
    return UserRepository()


@pytest_asyncio.fixture
def telegram_repository() -> TelegramAccountRepository:
    return TelegramAccountRepository()


@pytest_asyncio.fixture
def user_service(
    user_repository: UserRepository,
    telegram_repository: TelegramAccountRepository,
    message_bus: MessageBus,
) -> UserService:
    return UserService(
        repository=user_repository,
        telegram_repository=telegram_repository,
        message_bus=message_bus,
    )


@pytest_asyncio.fixture
def auth_token() -> str:
    """JWT-токен для тестового пользователя."""
    return create_access_token(str(uuid.uuid4()), role="user")


@pytest_asyncio.fixture
def admin_token() -> str:
    """JWT-токен для тестового администратора."""
    return create_access_token(str(uuid.uuid4()), role="admin")


@pytest_asyncio.fixture
async def auth_account(db_session: AsyncSession) -> Auth:
    """Создаёт тестовую учётную запись в БД."""
    from src.core.security import hash_password

    repo = AuthRepository()
    account = await repo.create(
        db_session,
        {
            "identifier": "test@example.com",
            "identifier_type": "email",
            "hashed_password": hash_password("testpassword"),
        },
    )
    return account


@pytest_asyncio.fixture
async def existing_auth_id(db_session: AsyncSession) -> uuid.UUID:
    """Создаёт AuthAccount и возвращает его ID для тестов."""
    repo = AuthRepository()
    account = await repo.create(
        db_session,
        {
            "identifier": "existing@test.com",
            "identifier_type": "email",
            "hashed_password": "hashed",
        },
    )
    return account.id


@pytest_asyncio.fixture
async def auth_token_for_account(auth_account: Auth) -> str:
    """JWT-токен для конкретной учётной записи."""
    return create_access_token(str(auth_account.id), auth_account.role)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Асинхронный HTTP-клиент для интеграционных тестов.
    Использует ASGITransport для прямого вызова FastAPI без сети.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
