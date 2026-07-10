"""
События модуля пользователей.
"""

import uuid

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class ProfileCreated(BaseEvent):
    """
    Событие: профиль пользователя создан.

    Публикуется при создании профиля через POST /users/.
    """

    event_name: str = BusTopics.PROFILE_CREATED
    auth_id: uuid.UUID
    profile_id: uuid.UUID


class ProfileUpdated(BaseEvent):
    """
    Событие: профиль пользователя обновлён.

    fields_updated — список изменённых полей,
    полезен для частичного обновления в других сервисах.
    """

    event_name: str = BusTopics.PROFILE_UPDATED
    auth_id: uuid.UUID
    profile_id: uuid.UUID
    fields_updated: list[str]


class ProfileDeleted(BaseEvent):
    """
    Событие: профиль пользователя удалён.

    Публикуется при удалении профиля через DELETE /users/me.
    """

    event_name: str = BusTopics.PROFILE_DELETED
    auth_id: uuid.UUID
    profile_id: uuid.UUID
