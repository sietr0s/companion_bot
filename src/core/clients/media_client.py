"""
Клиент для прямого вызова сервиса медиа-файлов.

Использует DI для получения сервиса и вызывает методы напрямую,
без HTTP-запросов. Для межмодульного взаимодействия в модульном монолите.
"""

import logging
import uuid

from src.core.database import create_async_session

logger = logging.getLogger(__name__)


class MediaClient:
    """
    Клиент для вызова методов MediaService напрямую.

    Получает сервис через прямое инстанцирование (без Depends).
    Session создаётся и закрывается внутри каждого метода.
    """

    @staticmethod
    def _get_service():
        """Получить экземпляр MediaService через прямое инстанцирование."""
        from src.bus import get_producer
        from src.modules.media.repository import StoredFileRepository
        from src.modules.media.service import MediaService
        from src.modules.media.storage.local import LocalStorage

        return MediaService(
            repository=StoredFileRepository(),
            storage=LocalStorage(),
            message_bus=get_producer(),
        )

    async def upload_media_to_storage(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        is_public: bool = False,
    ) -> str:
        """
        Загрузить файл в хранилище через прямой вызов сервиса.

        Args:
            file_bytes: Бинарные данные файла.
            filename: Имя файла.
            content_type: MIME-тип файла.
            is_public: Публичный ли файл.

        Returns:
            ID загруженного файла.

        Raises:
            Исключения пробрасываются наверх (ValueError, SQLAlchemyError и т.д.).
        """
        service = self._get_service()
        async with create_async_session() as session:
            stored_file = await service.upload(
                session,
                filename=filename,
                data=file_bytes,
                content_type=content_type,
                is_public=is_public,
            )
            return str(stored_file.id)

    async def get_media_file(self, file_id: str) -> bytes | None:
        """
        Скачать файл по ID через прямой вызов сервиса.

        Args:
            file_id: Идентификатор файла.

        Returns:
            Бинарные данные файла или None, если не найден.

        Raises:
            Исключения пробрасываются наверх (NotFoundError, SQLAlchemyError и т.д.).
        """
        service = self._get_service()
        file_uuid = uuid.UUID(file_id)
        async with create_async_session() as session:
            _, data = await service.download(session, file_uuid)
            return data

    async def delete_media_file(self, file_id: str) -> bool:
        """
        Удалить файл по ID через прямой вызов сервиса.

        Args:
            file_id: Идентификатор файла.

        Returns:
            True если успешно удалён.

        Raises:
            Исключения пробрасываются наверх (NotFoundError, SQLAlchemyError и т.д.).
        """
        service = self._get_service()
        file_uuid = uuid.UUID(file_id)
        async with create_async_session() as session:
            await service.delete(session, file_uuid)
            return True
