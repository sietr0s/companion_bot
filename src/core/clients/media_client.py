"""
Клиент для прямого вызова сервиса медиа-файлов.

Использует DI для получения сервиса и вызывает методы напрямую,
без HTTP-запросов. Для межмодульного взаимодействия в модульном монолите.
"""

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError

from src.core.database import get_session
from src.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class MediaClient:
    """
    Клиент для вызова методов MediaService напрямую.

    Получает сервис через фабрику зависимостей FastAPI.
    Session создаётся и закрывается внутри каждого метода.
    """

    async def upload_media_to_storage(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        is_public: bool = False,
    ) -> str | None:
        """
        Загрузить файл в хранилище через прямой вызов сервиса.

        Args:
            file_bytes: Бинарные данные файла.
            filename: Имя файла.
            content_type: MIME-тип файла.
            is_public: Публичный ли файл.

        Returns:
            ID загруженного файла или None при ошибке.
        """
        from src.modules.media.dependencies import get_media_service

        try:
            service = get_media_service()
            async for session in get_session():
                stored_file = await service.upload(
                    session,
                    filename=filename,
                    data=file_bytes,
                    content_type=content_type,
                    is_public=is_public,
                )
                return str(stored_file.id)
        except ValueError as e:
            logger.error("Ошибка валидации данных при загрузке %s: %s", filename, e)
            return None
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при загрузке медиа %s: %s", filename, e)
            raise
        except Exception as e:
            logger.exception("Неожиданная ошибка загрузки медиа в storage: %s (%s)", filename, e)
            return None

    async def get_media_file(self, file_id: str) -> bytes | None:
        """
        Скачать файл по ID через прямой вызов сервиса.

        Args:
            file_id: Идентификатор файла.

        Returns:
            Бинарные данные файла или None при ошибке.
        """
        from src.modules.media.dependencies import get_media_service

        try:
            service = get_media_service()
            file_uuid = uuid.UUID(file_id)
            async for session in get_session():
                _, data = await service.download(session, file_uuid)
                return data
        except ValueError as e:
            logger.error("Невалидный UUID файла %s: %s", file_id, e)
            return None
        except NotFoundError as e:
            logger.warning("Файл не найден %s: %s", file_id, e)
            return None
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при скачивании файла %s: %s", file_id, e)
            raise
        except Exception as e:
            logger.exception("Неожиданная ошибка при скачивании файла %s: %s", file_id, e)
            return None

    async def delete_media_file(self, file_id: str) -> bool:
        """
        Удалить файл по ID через прямой вызов сервиса.

        Args:
            file_id: Идентификатор файла.

        Returns:
            True если успешно удалён, False при ошибке.
        """
        from src.modules.media.dependencies import get_media_service

        try:
            service = get_media_service()
            file_uuid = uuid.UUID(file_id)
            async for session in get_session():
                await service.delete(session, file_uuid)
                return True
        except ValueError as e:
            logger.error("Невалидный UUID файла %s: %s", file_id, e)
            return False
        except NotFoundError as e:
            logger.warning("Файл не найден для удаления %s: %s", file_id, e)
            return False
        except SQLAlchemyError as e:
            logger.error("Ошибка БД при удалении файла %s: %s", file_id, e)
            raise
        except Exception as e:
            logger.exception("Неожиданная ошибка при удалении файла %s: %s", file_id, e)
            return False
