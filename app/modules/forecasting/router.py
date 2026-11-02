"""API de pronósticos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.forecasting import service as forecast_service
from app.modules.forecasting.schemas import ForecastOut
from app.shared.dependencies import DbSession, require_permission
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/forecasts", tags=["forecasting"])
CanView = Annotated[object, Depends(require_permission("predictions.view"))]


@router.get("", response_model=Page[ForecastOut])
def list_forecasts(
    db: DbSession,
    _: CanView,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sensor_id: int | None = None,
    site_id: int | None = None,
) -> Page[ForecastOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = forecast_service.list_forecasts(
        db,
        offset=params.offset,
        limit=params.page_size,
        sensor_id=sensor_id,
        site_id=site_id,
    )
    return Page(
        items=[ForecastOut.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{forecast_id}", response_model=ForecastOut)
def get_forecast(forecast_id: int, db: DbSession, _: CanView) -> ForecastOut:
    row = forecast_service.get_forecast(db, forecast_id)
    if row is None:
        raise NotFoundError("Pronóstico no encontrado")
    return ForecastOut.model_validate(row)
