"""Фикстуры для тестов модуля classifier."""

import pytest_asyncio
from sqlalchemy import text

from src.base.model import Base


@pytest_asyncio.fixture(autouse=True)
async def create_classifier_tables():
    """Создаёт таблицы classifier для каждого теста."""
    from tests.conftest import test_engine

    async with test_engine.begin() as conn:
        # Создаём все таблицы classifier
        await conn.run_sync(Base.metadata.create_all)
        
        # Включаем foreign keys для SQLite
        await conn.execute(text("PRAGMA foreign_keys=ON"))
    
    yield
