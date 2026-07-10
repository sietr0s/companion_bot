"""
Настройка подключения к PostgreSQL через SQLAlchemy 2.0 (async).

Асинхронный движок и сессия — основа для всех операций с БД.
Используем asyncpg как драйвер — он быстрее psycopg2 для I/O-bound нагрузки.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

# Создаём асинхронный движок.
# pool_size ограничивает количество одновременных подключений.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    echo=settings.DEBUG,
)

# Фабрика сессий — каждая сессия привязана к движку.
# expire_on_commit=False — объекты доступны после коммита без повторного запроса.
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий.

    Используется как зависимость в FastAPI (Depends).
    Сессия автоматически закрывается после завершения запроса.
    """
    async with async_session_factory() as session:
        yield session
