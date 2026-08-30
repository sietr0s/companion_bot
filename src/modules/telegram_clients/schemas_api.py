"""HTTP API schemas for telegram_clients module."""

from pydantic import BaseModel, Field
from uuid import UUID


# Auth schemas
class PhoneRequest(BaseModel):
    """Request to start phone authentication."""
    phone: str = Field(..., description="Phone number in international format")


class CodeRequest(BaseModel):
    """Request to verify phone code."""
    phone: str
    code: str
    phone_code_hash: str


class PasswordRequest(BaseModel):
    """Request to verify 2FA password."""
    phone: str
    password: str
    phone_code_hash: str


class AuthStep1Response(BaseModel):
    """Response after sending phone number (step 1)."""
    phone_code_hash: str
    message: str = "Code sent to your phone"


class AuthStep2Response(BaseModel):
    """Response after sending phone code (step 2)."""
    session_file: str | None = None
    message: str = "Authentication successful"


class AuthStep3Response(BaseModel):
    """Response after completing 2FA (step 3)."""
    session_file: str
    message: str = "2FA authentication successful"


# QR Auth schemas
class QrStartResponse(BaseModel):
    """Response when QR authentication is started."""
    token: str
    message: str = "QR code generated, scan it with Telegram app"


class QrStatusResponse(BaseModel):
    """Response with QR authentication status."""
    status: str  # pending, success, expired, failed
    message: str = ""


# Account schemas
class AccountRead(BaseModel):
    """Public account representation."""
    id: UUID
    phone: str
    status: str
    created_at: str
    updated_at: str | None = None

    class Config:
        from_attributes = True


class AccountCreate(BaseModel):
    """Request to create a new Telegram account."""
    phone: str


class AccountUpdate(BaseModel):
    """Request to update Telegram account."""
    status: str | None = None


# Chat state schemas
class ChatStateRead(BaseModel):
    """Public chat state representation."""
    id: UUID
    telegram_account_id: UUID
    chat_id: int
    last_read_message_id: int | None = None
    is_active: bool = True

    class Config:
        from_attributes = True


# Message schemas
class MessageRead(BaseModel):
    """Public message representation."""
    id: UUID
    telegram_account_id: UUID
    chat_id: int
    message_id: int
    text: str | None = None
    message_type: str
    direction: str  # incoming, outgoing
    created_at: str

    class Config:
        from_attributes = True


# Whitelist schemas
class WhitelistEntryCreate(BaseModel):
    """Request to add phone to whitelist."""
    phone: str


class WhitelistEntryRead(BaseModel):
    """Whitelist entry representation."""
    id: UUID
    phone: str
    created_at: str

    class Config:
        from_attributes = True
