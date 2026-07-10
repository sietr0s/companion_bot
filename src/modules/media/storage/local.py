"""
Локальное файловое хранилище.

Сохраняет файлы в папку на диске с 2-level sharding.
Пример ключа: ab/cd/abcd1234-5678-....jpg
"""

import uuid
from pathlib import Path

from src.core.config import settings

# Размер чанка для streaming (64 KB)
CHUNK_SIZE = 64 * 1024


def _generate_storage_key(filename: str) -> str:
    """
    Генерация ключа хранилища с 2-level sharding.

    Формат: {2_hex}/{2_hex}/{uuid4}.{ext}
    Пример: ab/cd/abcd1234-5678-....jpg
    """
    file_uuid = uuid.uuid4()
    hex_str = file_uuid.hex
    shard1 = hex_str[:2]
    shard2 = hex_str[2:4]

    ext = Path(filename).suffix if Path(filename).suffix else ""
    key = f"{shard1}/{shard2}/{file_uuid}{ext}"
    return key


class LocalStorage:
    """
    Локальное файловое хранилище.

    Файлы сохраняются в MEDIA_STORAGE_PATH с 2-level sharding.
    """

    def __init__(self, base_path: str | None = None):
        self._base_path = Path(base_path or settings.MEDIA_STORAGE_PATH)

    def _full_path(self, key: str) -> Path:
        """Полный путь к файлу на диске."""
        return self._base_path / key

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Сохранить файл на диск, вернуть key."""
        file_path = self._full_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return key

    async def get(self, key: str) -> bytes:
        """Прочитать файл с диска (для совместимости)."""
        file_path = self._full_path(key)
        return file_path.read_bytes()

    async def get_stream(self, key: str):
        """
        Читать файл потоком.

        Использует aiofiles для асинхронного чтения,
        чтобы не блокировать event loop.

        Args:
            key: Ключ файла в хранилище.

        Yields:
            bytes: Части файла размером CHUNK_SIZE.
        """
        import asyncio

        file_path = self._full_path(key)
        if not file_path.exists():
            return

        loop = asyncio.get_running_loop()

        # Читаем чанками в отдельном потоке
        def read_chunk(offset: int, size: int) -> bytes:
            """Читает чанк файла синхронно."""
            with open(file_path, "rb") as f:
                f.seek(offset)
                return f.read(size)

        file_size = file_path.stat().st_size
        offset = 0
        while offset < file_size:
            chunk = await loop.run_in_executor(None, read_chunk, offset, CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
            offset += len(chunk)

    async def delete(self, key: str) -> None:
        """Удалить файл с диска."""
        file_path = self._full_path(key)
        if file_path.exists():
            file_path.unlink()

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        """URL для скачивания через внутренний роут."""
        return f"/public/media/download/{key}"

    def ensure_base_path(self) -> None:
        """Создать базовую папку если не существует."""
        self._base_path.mkdir(parents=True, exist_ok=True)
