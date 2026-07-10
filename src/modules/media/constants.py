"""
Константы модуля медиа.
"""

from enum import StrEnum


class MediaType(StrEnum):
    """Типы контента для медиа."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    TEXT = "text"


# Сообщения об ошибках
ERROR_MESSAGES = {
    "file_not_found": "Файл не найден",
    "upload_failed": "Не удалось загрузить файл",
    "delete_failed": "Не удалось удалить файл",
    "storage_error": "Ошибка хранилища",
}
