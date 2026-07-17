"""
DI-зависимости модуля notifications.

Фабрики для внедрения NotificationService через FastAPI Depends.
"""

from fastapi import Depends

from src.modules.notifications.providers.base import NotificationProvider
from src.modules.notifications.providers.smtp import SmtpProvider
from src.modules.notifications.repository import (
    NotificationLogRepository,
    NotificationTemplateRepository,
)
from src.modules.notifications.service import NotificationService


def get_notification_template_repository() -> NotificationTemplateRepository:
    """Фабрика репозитория шаблонов уведомлений."""
    return NotificationTemplateRepository()


def get_notification_log_repository() -> NotificationLogRepository:
    """Фабрика репозитория логов уведомлений."""
    return NotificationLogRepository()


def get_notification_provider() -> NotificationProvider:
    """Провайдер уведомлений (SMTP по умолчанию)."""
    return SmtpProvider()


def get_notification_service(
    template_repo: NotificationTemplateRepository = Depends(get_notification_template_repository),
    log_repo: NotificationLogRepository = Depends(get_notification_log_repository),
    provider: NotificationProvider = Depends(get_notification_provider),
) -> NotificationService:
    """Фабрика сервиса нотификаций."""
    return NotificationService(
        template_repo=template_repo,
        log_repo=log_repo,
        provider=provider,
    )


def get_notification_service_factory():
    """
    Фабрика (session, service) для обработчиков шины.

    Возвращает кортеж (session, NotificationService) для использования
    в обработчиках событий шины.
    """
    return NotificationService(
        template_repo=NotificationTemplateRepository(),
        log_repo=NotificationLogRepository(),
        provider=SmtpProvider(),
    )
