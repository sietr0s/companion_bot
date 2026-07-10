"""Схемы лога уведомлений модуля notifications."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationLogRead(BaseModel):
    """Лог отправки уведомления."""

    id: uuid.UUID
    auth_id: uuid.UUID
    channel: str
    template_name: str
    recipient: str
    subject: str | None = None
    body: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
