"""
Pydantic-схемы для API модуля media.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class FileRead(BaseModel):
    """Ответ с метаданными файла."""

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    """Ответ после загрузки файла."""

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
