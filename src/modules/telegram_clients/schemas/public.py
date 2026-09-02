"""Публичные HTTP-схемы модуля telegram_clients."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PhoneRequest(BaseModel):
    phone: str = Field(..., description="Phone number in international format")


class CodeRequest(BaseModel):
    account_id: UUID
    code: str


class PasswordRequest(BaseModel):
    account_id: UUID
    password: str


class AuthStep1Response(BaseModel):
    account_id: UUID
    phone_code_hash: str | None = None
    message: str = "Code sent to your phone"


class AuthStep2Response(BaseModel):
    account_id: UUID
    status: str | None = None
    message: str = "Authentication successful"


class AuthStep3Response(BaseModel):
    account_id: UUID
    status: str | None = None
    message: str = "2FA authentication successful"


class QrStartResponse(BaseModel):
    account_id: UUID
    qr_url: str | None = None
    expires_at: datetime | str | None = None
    message: str = "QR code generated, scan it with Telegram app"


class QrStatusResponse(BaseModel):
    status: str
    message: str = ""


class AccountRead(BaseModel):
    id: UUID
    phone: str
    telegram_id: int | None = None
    is_connected: bool = False
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AccountCreate(BaseModel):
    phone: str
    session_file: str = ""
    is_connected: bool = False
    telegram_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class AccountUpdate(BaseModel):
    phone: str | None = None
    is_connected: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    session_file: str | None = None


class ChatRead(BaseModel):
    id: int | None = None
    title: str | None = None
    type: str | None = None
    username: str | None = None
    is_in_whitelist: bool | None = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class MediaItem(BaseModel):
    id: str
    type: str


class MessageRead(BaseModel):
    id: int | UUID | None = None
    chat_id: int
    sender_id: int | None = None
    text: str | None = None
    media: list[MediaItem] = Field(default_factory=list)
    date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatStateCreate(BaseModel):
    account_id: UUID
    chat_id: int
    last_read_message_id: int


class ChatStateUpdate(BaseModel):
    last_read_message_id: int | None = None


class ChatStateRead(BaseModel):
    id: UUID
    account_id: UUID
    chat_id: int
    last_read_message_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TelegramSettingsCreate(BaseModel):
    account_id: UUID | None = None
    use_whitelist: bool = True
    whitelist_chat_ids: list[int] = Field(default_factory=list)


class TelegramSettingsUpdate(BaseModel):
    use_whitelist: bool | None = None
    whitelist_chat_ids: list[int] | None = None


class TelegramSettingsRead(BaseModel):
    id: UUID
    account_id: UUID
    use_whitelist: bool
    whitelist_chat_ids: list | None = None

    model_config = ConfigDict(from_attributes=True)


class WhitelistEntryCreate(BaseModel):
    chat_id: int
