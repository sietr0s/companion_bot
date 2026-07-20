"""Internal API-схемы подписок на вакансии."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SubscriptionRead(BaseModel):
    """Подписка пользователя для административного интерфейса."""

    id: uuid.UUID
    auth_id: uuid.UUID
    keywords: list[str] | None = None
    category_ids: list[uuid.UUID] | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    locations: list[str] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
