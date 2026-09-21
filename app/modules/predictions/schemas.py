"""Schemas de predicciones."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    id: int
    gas_reading_id: int
    model_registry_id: int
    probability: float
    predicted_label: int
    risk_level: str
    created_at: datetime

    model_config = {"from_attributes": True}
