"""Esquemas del catálogo."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class GasTypeOut(BaseModel):
    code: str
    display_name: str
    plain_description: str
    canonical_unit: str
    lel_percent_vol: Optional[float] = None
    physical_max: Optional[float] = None
    max_rate_per_min: Optional[float] = None
    priority: int
    is_active: bool

    model_config = {"from_attributes": True}


class ThresholdOut(BaseModel):
    id: int
    gas_code: str
    level: str
    direction: str
    value: float
    source_reference: str
    verified: bool
    valid_from: datetime

    model_config = {"from_attributes": True}


class SettingOut(BaseModel):
    key: str
    value: Any
