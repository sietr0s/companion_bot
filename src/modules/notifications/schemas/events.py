"""
События модуля нотификаций.
"""

import uuid

from pydantic import Field

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class NotificationSend(BaseEvent):
    """
    Событие: отправить уведомление.

    Любой модуль публикует это событие, notifications
    обрабатывает и отправляет email/sms.
    """

    event_name: str = BusTopics.NOTIFICATION_SEND
    auth_id: uuid.UUID
    template_name: str
    channel: str = "email"
    body: dict = Field(default_factory=dict)
