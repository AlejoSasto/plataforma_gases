"""Schemas de reportes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PeriodRequest(BaseModel):
    start: date
    end: date


class EjecutivoRequest(BaseModel):
    start: date
    end: date
    stakeholder_id: Optional[int] = None
    formato: str = "pdf"


class ReportResponse(BaseModel):
    id: int
    type: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    file_path: str
    generated_by: Optional[int] = None
    created_at: datetime
    download_url: str

    model_config = {"from_attributes": True}


class ReportCreateResponse(BaseModel):
    report: ReportResponse
    message: str = "Reporte generado"
