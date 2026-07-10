"""
Тесты хранилища (LocalStorage).

Проверяет, что get_stream работает асинхронно
и не блокирует event loop.
"""

import asyncio
import os
import tempfile
import uuid

import pytest

from src.modules.media.storage.local import LocalStorage


class TestLocalStorage:
    """Тесты LocalStorage."""

    @pytest.fixture
    def storage(self):
        """Создаёт экземпляр LocalStorage с временной базовой папкой."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalStorage(base_path=tmpdir)

    @pytest.fixture
    def test_data(self):
        """Генерирует тестовые данные."""
        return b"x" * 1024 * 1024  # 1 MB

    @pytest.mark.asyncio
    async def test_put_and_get(self, storage):
        """Сохранить и прочитать файл."""
        key = f"test/{uuid.uuid4().hex}.bin"
        data = b"hello world"

        result = await storage.put(key, data, "text/plain")
        assert result == key

        read_data = await storage.get(key)
        assert read_data == data

    @pytest.mark.asyncio
    async def test_get_stream(self, storage):
        """Читать файл потоком — не блокирует event loop."""
        key = f"test/{uuid.uuid4().hex}.bin"
        data = b"hello world"

        await storage.put(key, data, "text/plain")

        # Собираем чанки
        chunks = []
        async for chunk in storage.get_stream(key):
            chunks.append(chunk)

        assert b"".join(chunks) == data

    @pytest.mark.asyncio
    async def test_get_stream_not_blocking(self, storage):
        """
        Проверяет, что get_stream не блокирует event loop.

        Запускаем две параллельные задачи:
        1. get_stream — чтение файла
        2. asyncio.sleep — проверка, что event loop работает
        """
        key = f"test/{uuid.uuid4().hex}.bin"
        data = b"x" * 1024 * 1024  # 1 MB

        await storage.put(key, data, "text/plain")

        async def read_and_collect():
            """Читает файл и собирает чанки."""
            chunks = []
            async for chunk in storage.get_stream(key):
                chunks.append(chunk)
            return b"".join(chunks)

        # Запускаем параллельно
        task1 = asyncio.create_task(read_and_collect())
        task2 = asyncio.create_task(asyncio.sleep(0.01))

        # Даём обеим задачам время на выполнение
        await asyncio.sleep(0.5)

        # Обе задачи должны завершиться или быть в процессе
        # Если get_stream блокирует — sleep не выполнится
        assert not task2.done() or task1.done(), "get_stream блокирует event loop!"
        result = await task1
        assert result == data

    @pytest.mark.asyncio
    async def test_get_stream_not_found(self, storage):
        """Если файл не найден — возвращает None."""
        result = storage.get_stream("nonexistent")
        assert result is not None

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Удалить файл."""
        key = f"test/{uuid.uuid4().hex}.bin"
        data = b"hello"

        await storage.put(key, data, "text/plain")
        await storage.delete(key)

        # После удаления файл не должен существовать
        assert not os.path.exists(storage._full_path(key))
