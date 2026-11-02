"""Schemas Pydantic de autenticación."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    totp_code: str | None = None
    keep_session: bool = False


class UserMeResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[str]
    permissions: list[str]
    must_change_password: bool = False
    totp_enabled: bool = False
    totp_required: bool = False

    model_config = {"from_attributes": True}
