"""
Абстракция файлового хранилища.

StorageProvider — Protocol, который реализуют
конкретные хранилища (LocalStorage, S3Storage).
"""

from collections.abc import AsyncGenerator
from typing import Protocol


class StorageProvider(Protocol):
    """
    Интерфейс файлового хранилища.

    Каждое хранилище реализует методы put/get/delete/generate_url.
    """

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Сохранить файл, вернуть key."""
        ...

    async def get(self, key: str) -> bytes:
        """Прочитать файл из хранилища (для совместимости)."""
        ...

    async def get_stream(self, key: str) -> AsyncGenerator[bytes, None]:
        """
        Читать файл потоком.

        Yields:
            bytes: Части файла (chunks).
        """
        ...

    async def delete(self, key: str) -> None:
        """Удалить файл."""
        ...

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        """Сгенерировать URL для скачивания."""
        ...
