"""Router de alertas."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.alerts import service as alerts_service
from app.modules.alerts.schemas import AlertResponse, ResolveAlertRequest
from app.modules.stakeholders.service import alert_ids_visible_to_user
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.exceptions import NotFoundError, PermissionDeniedError
from app.shared.pagination import Page, PageParams

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

CanView = Annotated[object, Depends(require_permission("alerts.view"))]
CanResolve = Annotated[object, Depends(require_permission("alerts.resolve"))]


@router.get("", response_model=Page[AlertResponse])
def list_alerts(
    db: DbSession,
    actor: CurrentUser,
    _: CanView,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    level: str | None = None,
    site_id: int | None = None,
) -> Page[AlertResponse]:
    params = PageParams(page=page, page_size=page_size)
    visible = alert_ids_visible_to_user(db, actor.id)
    items, total = alerts_service.list_alerts(
        db,
        offset=params.offset,
        limit=params.page_size,
        status=status,
        level=level,
        site_id=site_id,
        visible_ids=visible,
    )
    return Page(
        items=[AlertResponse(**alerts_service.alert_to_dict(db, a)) for a in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int, db: DbSession, actor: CurrentUser, _: CanView
) -> AlertResponse:
    alert = alerts_service.get_alert(db, alert_id)
    if alert is None:
        raise NotFoundError("Alerta no encontrada")
    visible = alert_ids_visible_to_user(db, actor.id)
    if visible is not None and alert_id not in visible:
        raise PermissionDeniedError("Alerta fuera de tus suscripciones")
    return AlertResponse(**alerts_service.alert_to_dict(db, alert))


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    db: DbSession,
    actor: CurrentUser,
    _: CanResolve,
) -> AlertResponse:
    alert = alerts_service.acknowledge_alert(db, alert_id, actor)
    return AlertResponse(**alerts_service.alert_to_dict(db, alert))


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: DbSession,
    actor: CurrentUser,
    _: CanResolve,
    body: ResolveAlertRequest | None = None,
) -> AlertResponse:
    note = body.resolution_note if body else None
    alert = alerts_service.resolve_alert(db, alert_id, actor, note)
    return AlertResponse(**alerts_service.alert_to_dict(db, alert))
