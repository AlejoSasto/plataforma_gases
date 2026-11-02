"""Schemas de usuarios."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    full_name: str = Field(min_length=1, max_length=255)
    role_ids: list[int] = Field(default_factory=list)
    site_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=12)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class UserRolesUpdate(BaseModel):
    role_ids: list[int]


class UserSitesUpdate(BaseModel):
    site_ids: list[int] = Field(default_factory=list)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    must_change_password: bool = False
    locked: bool = False
    site_ids: list[int] = Field(default_factory=list)
    status: str = "activo"

    model_config = {"from_attributes": True}
