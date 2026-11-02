"""Schemas de alertas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: int
    forecast_id: Optional[int] = None
    kind: Optional[str] = None
    gas_reading_id: Optional[int] = None
    sensor_id: int
    sensor_code: Optional[str] = None
    gas_type: Optional[str] = None
    site_name: Optional[str] = None
    level: str
    message: str
    recommendation: str
    status: str
    created_at: datetime
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    resolution_note: Optional[str] = Field(default=None, max_length=2000)
