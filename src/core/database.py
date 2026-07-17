"""
Настройка подключения к PostgreSQL через SQLAlchemy 2.0 (async).

Асинхронный движок и сессия — основа для всех операций с БД.
Используем asyncpg как драйвер — он быстрее psycopg2 для I/O-bound нагрузки.
"""
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.base.model import Base

logger = logging.getLogger(__name__)

async_session_factory: callable


async def init_db() -> None:
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        echo=settings.DEBUG,
    )
    global async_session_factory
    if not async_session_factory:
        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    if settings.CREATE_TABLES_ON_STARTUP:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД созданы")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий.

    Используется как зависимость в FastAPI (Depends).
    Сессия автоматически закрывается после завершения запроса.
    """
    async with async_session_factory() as session:
        yield session
