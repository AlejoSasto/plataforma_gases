"""Schemas Pydantic de ingesta."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class EtlRunResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    rows_ingested: int
    rows_rejected: int
    source_files: list[Any] = Field(default_factory=list)
    log: dict[str, Any] = Field(default_factory=dict)
    triggered_by_user_id: Optional[int] = None

    model_config = {"from_attributes": True}
