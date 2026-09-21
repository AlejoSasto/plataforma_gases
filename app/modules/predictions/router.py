"""Router de predicciones."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.predictions import service as pred_service
from app.modules.predictions.schemas import PredictionResponse
from app.shared.dependencies import DbSession, require_permission
from app.shared.exceptions import NotFoundError
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

CanView = Annotated[object, Depends(require_permission("predictions.view"))]


@router.get("", response_model=Page[PredictionResponse])
def list_predictions(
    db: DbSession,
    _: CanView,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sensor_id: int | None = None,
    site_id: int | None = None,
) -> Page[PredictionResponse]:
    params = PageParams(page=page, page_size=page_size)
    items, total = pred_service.list_predictions(
        db,
        offset=params.offset,
        limit=params.page_size,
        sensor_id=sensor_id,
        site_id=site_id,
    )
    return Page(
        items=[PredictionResponse.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(
    prediction_id: int, db: DbSession, _: CanView
) -> PredictionResponse:
    pred = pred_service.get_prediction(db, prediction_id)
    if pred is None:
        raise NotFoundError("Predicción no encontrada")
    return PredictionResponse.model_validate(pred)
