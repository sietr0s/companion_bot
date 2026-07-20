"""
Обработчики событий модуля нотификаций.

Подписка на топик notification.send — основной вход
для отправки уведомлений из других модулей.
"""

import logging
import uuid

from src.bus import get_consumer
from src.bus.interface import MessageConsumer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.notifications.dependencies import get_notification_service_factory

logger = logging.getLogger(__name__)


def register_handlers(consumer: MessageConsumer | None = None) -> None:
    """
    Регистрация обработчиков событий на шину.

    notification_service_factory — async callable, возвращающий
    кортеж (session, NotificationService).
    """

    bus = consumer or get_consumer()

    @bus.subscribe(BusTopics.NOTIFICATION_SEND)
    async def handle_notification_send(message: dict) -> None:
        """Обработчик: отправить уведомление."""
        auth_id_str = message.get("auth_id")
        template_name = message.get("template_name")
        channel = message.get("channel", "email")
        body = message.get("body", {})

        if not auth_id_str or not template_name:
            logger.warning("Неполные данные для уведомления: %s", message)
            return

        # Получаем сервис и отправляем
        service = get_notification_service_factory()

        async with create_async_session() as session:
            await service.send_notification(
                session=session,
                auth_id=uuid.UUID(auth_id_str),
                template_name=template_name,
                channel=channel,
                body=body,
            )
