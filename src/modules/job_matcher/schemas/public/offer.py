"""Public API-схемы вакансий job_matcher."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class JobOfferAdminRead(BaseModel):
    """Вакансия, доступная администратору frontend."""

    id: uuid.UUID
    title: str
    description: str | None = None
    tags: list[str] | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    location: str | None = None
    source_chat_id: int
    source_message_id: int
    telegram_sender_id: int | None = None
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    category_ids: list[uuid.UUID] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
