"""Esquemas de pronósticos."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ForecastQuantileOut(BaseModel):
    horizon_min: int
    q10: Optional[float] = None
    q50: Optional[float] = None
    q90: Optional[float] = None
    q95: Optional[float] = None

    model_config = {"from_attributes": True}


class ForecastOut(BaseModel):
    id: int
    sensor_id: int
    model_id: int
    issued_at: datetime
    status_level: str
    exceed_prob: Optional[dict[str, Any]] = None
    confidence: str
    latency_ms: Optional[int] = None
    created_at: datetime
    quantiles: list[ForecastQuantileOut] = []

    model_config = {"from_attributes": True}
