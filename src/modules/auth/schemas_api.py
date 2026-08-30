"""HTTP API схемы для модуля auth."""

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Generic, TypeVar

from src.base.schemas import PaginatedResponse


class AccountCreate(BaseModel):
    """Schema for creating a new account."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "user"


class AccountUpdate(BaseModel):
    """Schema for updating an account."""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class AccountResponse(BaseModel):
    """Schema for account response."""
    id: UUID
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr
    password: str


class PasswordUpdate(BaseModel):
    """Schema for password update."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# Alias для пагинированного ответа
AccountPageResponse = PaginatedResponse[AccountResponse]
