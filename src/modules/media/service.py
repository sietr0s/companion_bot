"""
Сервис модуля media.

Управляет загрузкой, получением и удалением файлов.
Делегирует хранение StorageProvider, персистентность — репозиторию.
"""

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.filters import Filter
from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.exceptions import NotFoundError
from src.modules.media.constants import ERROR_MESSAGES
from src.modules.media.models import StoredFile
from src.modules.media.repository import StoredFileRepository
from src.modules.media.schemas.events import MediaDeleted, MediaUploaded
from src.modules.media.storage.base import StorageProvider
from src.modules.media.storage.local import _generate_storage_key


class MediaService(BaseService[StoredFileRepository, StoredFile]):
    """
    Сервис управления файлами.

    Координирует работу репозитория, StorageProvider и шины событий.
    """

    def __init__(
        self,
        repository: StoredFileRepository,
        storage: StorageProvider,
        message_bus: MessageProducer,
    ) -> None:
        super().__init__(repository)
        self.storage = storage
        self.message_bus = message_bus

    async def upload(
        self,
        session: AsyncSession,
        filename: str,
        data: bytes,
        content_type: str,
        is_public: bool = False,
    ) -> StoredFile:
        """
        Загрузить файл.

        1. Генерирует storage_key
        2. Сохраняет через StorageProvider
        3. Создаёт запись в БД
        4. Публикует событие MEDIA_UPLOADED
        """
        storage_key = _generate_storage_key(filename)
        await self.storage.put(storage_key, data, content_type)

        stored_file = await self.repository.create(
            session,
            {
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(data),
                "storage_key": storage_key,
                "is_public": is_public,
            },
        )

        await self.message_bus.publish(
            BusTopics.MEDIA_UPLOADED,
            MediaUploaded(
                file_id=stored_file.id,
                filename=stored_file.filename,
                content_type=stored_file.content_type,
                size_bytes=stored_file.size_bytes,
                is_public=stored_file.is_public,
            ).to_bus_dict(),
        )

        return stored_file

    async def get(self, session: AsyncSession, file_id: uuid.UUID) -> StoredFile:
        """Получить метаданные файла по ID."""
        stored_file = await self.repository.get_by_id(session, file_id)
        if not stored_file:
            raise NotFoundError(detail=ERROR_MESSAGES["file_not_found"])
        return stored_file

    async def download(self, session: AsyncSession, file_id: uuid.UUID) -> tuple[StoredFile, bytes]:
        """
        Скачать файл (для совместимости).

        Возвращает кортеж (метаданные, бинарные данные).
        """
        stored_file = await self.get(session, file_id)
        data = await self.storage.get(stored_file.storage_key)
        return stored_file, data

    async def download_stream(
        self, session: AsyncSession, file_id: uuid.UUID
    ) -> tuple[StoredFile, AsyncGenerator[bytes, None]]:
        """
        Скачать файл потоком.

        Args:
            session: Сессия БД.
            file_id: UUID файла.

        Returns:
            Кортеж (метаданные, асинхронный генератор чанков).
        """
        stored_file = await self.get(session, file_id)
        stream = self.storage.get_stream(stored_file.storage_key)
        return stored_file, stream

    async def delete(self, session: AsyncSession, file_id: uuid.UUID) -> None:
        """
        Удалить файл.

        1. Удаляет из хранилища
        2. Удаляет из БД
        3. Публикует событие MEDIA_DELETED
        """
        stored_file = await self.get(session, file_id)
        await self.storage.delete(stored_file.storage_key)
        await self.repository.delete(session, stored_file)

        await self.message_bus.publish(
            BusTopics.MEDIA_DELETED,
            MediaDeleted(file_id=file_id).to_bus_dict(),
        )

    async def get_user_files(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: list[Filter] | None = None,
        order_by: str | None = "-created_at",
    ) -> tuple[list[StoredFile], int]:
        """Получить список всех файлов с фильтрацией и пагинацией."""
        return await self.repository.get_list(session, filters, skip, limit, order_by)

    async def update_file(
        self,
        session: AsyncSession,
        file_id: uuid.UUID,
        is_public: bool | None = None,
        filename: str | None = None,
    ) -> StoredFile:
        """Обновить метаданные файла."""
        stored_file = await self.get(session, file_id)

        update_data = {}
        if is_public is not None:
            update_data["is_public"] = is_public
        if filename is not None:
            update_data["filename"] = filename

        if update_data:
            stored_file = await self.repository.update(session, stored_file, update_data)

        return stored_file
