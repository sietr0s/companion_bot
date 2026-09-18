"""HTTP-схемы собеседников."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    platform: str = Field(max_length=32)
    platform_user_id: str = Field(max_length=64)
    username: str | None = Field(None, max_length=100)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    notes: str | None = None


class UserUpdate(BaseModel):
    username: str | None = Field(None, max_length=100)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    notes: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: str
    platform_user_id: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
