"""Schemas de predicciones."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    id: int
    gas_reading_id: int
    model_registry_id: int
    probability: float
    predicted_label: int
    risk_level: str
    predicted_concentration: Optional[float] = None
    horizon_minutes: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
