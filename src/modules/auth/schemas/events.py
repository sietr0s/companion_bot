"""
События модуля авторизации (Event-Driven Architecture).

События публикуются в шину после успешных операций.
Другие модули подписываются на них и реагируют
без прямых связей между модулями.
"""

import uuid

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class UserRegistered(BaseEvent):
    """
    Событие: пользователь зарегистрирован.

    Модуль users может подписаться на это событие
    для логирования или других реакций.
    """

    event_name: str = BusTopics.USER_REGISTERED
    auth_id: uuid.UUID
    identifier: str
    identifier_type: str


class UserLoggedIn(BaseEvent):
    """
    Событие: пользователь авторизовался.

    Может использоваться для логирования,
    аналитики и обновления статуса онлайн.
    """

    event_name: str = BusTopics.USER_LOGGED_IN
    auth_id: uuid.UUID
    identifier: str
    identifier_type: str


class UserDeleted(BaseEvent):
    """
    Событие: учётная запись удалена.

    Модуль users может подписаться для
    каскадного удаления профиля.
    """

    event_name: str = BusTopics.USER_DELETED
    auth_id: uuid.UUID
