"""APIs JSON de soporte para el dashboard."""

from __future__ import annotations

from typing import Annotated, Optional

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.modules.dashboard import service as dash_service
from app.shared.dependencies import CurrentUser, DbSession, require_permission

router = APIRouter(prefix="/dashboard/api", tags=["dashboard"])

CanViewPred = Annotated[object, Depends(require_permission("predictions.view"))]
CanViewAlerts = Annotated[object, Depends(require_permission("alerts.view"))]
CanViewSites = Annotated[
    object,
    Depends(require_permission("predictions.view")),
]


@router.get("/semaforo")
def api_semaforo(
    db: DbSession,
    user: CurrentUser,
    _: CanViewPred,
    site_id: Optional[int] = None,
) -> dict:
    items = dash_service.semaforo(db, site_id=site_id)
    return {
        "items": items,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/series/{sensor_id}")
def api_series(
    sensor_id: int,
    db: DbSession,
    _: CanViewPred,
    hours: int = Query(24, ge=1, le=24 * 90),
) -> dict:
    return dash_service.series_for_sensor(db, sensor_id, hours=hours)


@router.get("/alertas-activas")
def api_alertas_activas(
    db: DbSession,
    user: CurrentUser,
    _: CanViewAlerts,
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    return {"items": dash_service.alertas_activas(db, user_id=user.id, limit=limit)}


@router.get("/sites")
def api_sites(db: DbSession, _: CanViewSites) -> dict:
    return {"items": dash_service.list_sites(db)}


@router.get("/executive")
def api_executive(
    db: DbSession,
    user: CurrentUser,
    _: CanViewAlerts,
    days: int = Query(30, ge=1, le=365),
) -> dict:
    return dash_service.executive_kpis(db, days=days, user_id=user.id)


@router.get("/ingeniero")
def api_ingeniero(
    db: DbSession,
    _: Annotated[object, Depends(require_permission("sensors.manage"))],
) -> dict:
    return dash_service.ingeniero_snapshot(db)
