"""Публичные HTTP-схемы модуля instagram_clients."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InstagramLoginRequest(BaseModel):
    username: str
    password: str


class InstagramCodeRequest(BaseModel):
    code: str


class InstagramAccountCreate(BaseModel):
    username: str = Field(max_length=100)


class InstagramAccountUpdate(BaseModel):
    username: str | None = Field(None, max_length=100)
    is_connected: bool | None = None
    full_name: str | None = None
    instagram_pk: int | None = None


class InstagramAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    instagram_pk: int | None = None
    session_file: str
    is_connected: bool = False
    full_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InstagramSettingsCreate(BaseModel):
    account_id: UUID | None = None
    use_whitelist: bool = True
    whitelist_user_pks: list[int] = Field(default_factory=list)


class InstagramSettingsUpdate(BaseModel):
    use_whitelist: bool | None = None
    whitelist_user_pks: list[int] | None = None


class InstagramSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    use_whitelist: bool
    whitelist_user_pks: list | None = None


class InstagramWhitelistEntryCreate(BaseModel):
    user_pk: int


class InstagramChatStateCreate(BaseModel):
    account_id: UUID
    thread_id: int
    last_item_id: str


class InstagramChatStateUpdate(BaseModel):
    last_item_id: str | None = None


class InstagramChatStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    thread_id: int
    last_item_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
