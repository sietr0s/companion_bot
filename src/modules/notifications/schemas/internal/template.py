"""Internal API схемы модуля notifications."""

import uuid

from pydantic import BaseModel, Field


class SendNotificationRequest(BaseModel):
    """Запрос на отправку уведомления (internal)."""

    auth_id: uuid.UUID
    template_name: str = Field(..., description="Имя шаблона")
    channel: str = Field(default="email", description="Канал отправки (email, sms, push)")
    body: dict = Field(default_factory=dict, description="Данные для рендера шаблона")


class RenderTemplateRequest(BaseModel):
    """Запрос на тестовый рендер шаблона."""

    template_name: str
    body: dict = Field(default_factory=dict)


class RenderTemplateResponse(BaseModel):
    """Ответ с результатом рендера."""

    subject: str
    body: str
