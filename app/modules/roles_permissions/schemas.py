"""Schemas de roles y permisos."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: int
    code: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: Optional[str] = None
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = None
    permission_ids: Optional[list[int]] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: list[str]

    model_config = {"from_attributes": True}
