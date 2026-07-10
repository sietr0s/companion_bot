"""Схемы шаблонов уведомлений модуля notifications."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    """Создание шаблона уведомления."""

    name: str = Field(..., description="Название шаблона", max_length=100)
    channel: str = Field(..., description="Канал отправки (email, sms, push)", max_length=20)
    subject_template: str | None = None
    body_template: str = Field(..., description="Тело шаблона (Jinja2)")
    is_active: bool = True


class TemplateRead(BaseModel):
    """Просмотр шаблона."""

    id: uuid.UUID
    name: str
    channel: str
    subject_template: str | None = None
    body_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateUpdate(BaseModel):
    """Обновление шаблона (partial update)."""

    name: str | None = Field(default=None, max_length=100)
    channel: str | None = Field(default=None, max_length=20)
    subject_template: str | None = None
    body_template: str | None = None
    is_active: bool | None = None
