"""Schemas Pydantic de stakeholders."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class StakeholderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(pattern="^(interno|externo)$")
    organization: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notify_channels: list[str] = Field(default_factory=lambda: ["email"])
    user_id: Optional[int] = None


class StakeholderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    type: Optional[str] = Field(default=None, pattern="^(interno|externo)$")
    organization: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notify_channels: Optional[list[str]] = None


class StakeholderResponse(BaseModel):
    id: int
    name: str
    type: str
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notify_channels: list[Any] = Field(default_factory=list)
    created_at: datetime
    user_ids: list[int] = Field(default_factory=list)


class SubscriptionCreate(BaseModel):
    site_id: Optional[int] = None
    sensor_id: Optional[int] = None
    min_level: str = "ALERTA"


class SubscriptionResponse(BaseModel):
    id: int
    stakeholder_id: int
    site_id: Optional[int] = None
    sensor_id: Optional[int] = None
    min_level: str
    created_at: datetime
