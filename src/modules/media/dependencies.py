"""
DI-зависимости модуля media.

Фабрики для внедрения MediaService и StorageProvider
через FastAPI Depends.
"""

from fastapi import Depends

from src.bus import get_producer
from src.modules.media.repository import StoredFileRepository
from src.modules.media.service import MediaService
from src.modules.media.storage.base import StorageProvider


def get_stored_file_repository() -> StoredFileRepository:
    """Фабрика репозитория файлов."""
    return StoredFileRepository()


def get_storage_provider() -> StorageProvider:
    """Провайдер хранилища (LocalStorage по умолчанию)."""
    from src.modules.media.storage.local import LocalStorage

    return LocalStorage()


def get_media_service(
    repo: StoredFileRepository = Depends(get_stored_file_repository),
    storage: StorageProvider = Depends(get_storage_provider),
) -> MediaService:
    """Фабрика сервиса media."""
    return MediaService(repository=repo, storage=storage, message_bus=get_producer())
