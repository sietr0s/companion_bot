"""
Константы модуля уведомлений.
"""

from enum import StrEnum


class NotificationChannel(StrEnum):
    """Типы каналов уведомлений."""

    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"


class NotificationStatus(StrEnum):
    """Статусы отправки уведомлений."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# Сообщения об ошибках
ERROR_MESSAGES = {
    "template_not_found": "Шаблон не найден",
    "recipient_not_found": "Не удалось получить получателя",
    "send_failed": "Не удалось отправить уведомление",
}
