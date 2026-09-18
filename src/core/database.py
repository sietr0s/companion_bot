"""
Настройка подключения к PostgreSQL через SQLAlchemy 2.0 (async).

Асинхронный движок и сессия — основа для всех операций с БД.
Используем asyncpg как драйвер — он быстрее psycopg2 для I/O-bound нагрузки.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.base.model import Base
from src.core.config import settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Возвращает фабрику сессий. Должна быть инициализирована через init_db()."""
    if _async_session_factory is None:
        raise RuntimeError(
            "async_session_factory не инициализирована. Вызовите init_db() перед использованием."
        )
    return _async_session_factory


def create_async_session() -> AsyncSession:
    """Создать новую асинхронную сессию БД."""
    factory = get_async_session_factory()
    return factory()


async def init_db() -> None:
    global _engine, _async_session_factory

    _engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        echo=False,
    )
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    if settings.CREATE_TABLES_ON_STARTUP:
        async with _engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД созданы")


async def dispose_db() -> None:
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _async_session_factory = None


def _load_models() -> None:
    """Импортировать ORM-модели, чтобы они попали в Base.metadata."""
    from src.modules.auth.models import Auth  # noqa: F401
    from src.modules.behavior.models import BehaviorAccountState, BehaviorChatState  # noqa: F401
    from src.modules.memory.models import (  # noqa: F401
        Conversation,
        Message,
        MessageBatch,
        SummaryState,
        VectorRecord,
    )
    from src.modules.telegram_clients.models import (  # noqa: F401
        TelegramAccount,
        TelegramChatState,
        TelegramSettings,
    )
    from src.modules.users.models import User  # noqa: F401
    from src.modules.instagram_clients.models import (  # noqa: F401
        InstagramAccount,
        InstagramChatState,
        InstagramSettings,
    )


_load_models()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий.

    Используется как зависимость в FastAPI (Depends).
    Сессия автоматически закрывается после завершения запроса.
    """
    async with create_async_session() as session:
        yield session
