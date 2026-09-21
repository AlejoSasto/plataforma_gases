"""Vistas HTML del dashboard y pantallas del Plan 11."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.security import hash_password, verify_password
from app.modules.alerts import service as alerts_service
from app.modules.dashboard import service as dash_service
from app.modules.dashboard.nav import template_context
from app.modules.ml_training import service as ml_service
from app.modules.ml_training.repository import get_model
from app.modules.stakeholders import service as stake_service
from app.modules.users import service as users_service
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.exceptions import NotFoundError, PermissionDeniedError
from app.shared.pagination import PageParams

router = APIRouter(tags=["ui"])
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))

CanAlerts = Annotated[object, Depends(require_permission("alerts.view"))]
CanResolve = Annotated[object, Depends(require_permission("alerts.resolve"))]
CanSensors = Annotated[object, Depends(require_permission("sensors.manage"))]
CanTrain = Annotated[object, Depends(require_permission("models.train"))]
CanUsers = Annotated[object, Depends(require_permission("users.manage"))]
CanRoles = Annotated[object, Depends(require_permission("roles.manage"))]
CanStake = Annotated[object, Depends(require_permission("stakeholders.manage"))]
CanAudit = Annotated[object, Depends(require_permission("audit.view"))]
CanReports = Annotated[object, Depends(require_permission("reports.export"))]
CanPred = Annotated[object, Depends(require_permission("predictions.view"))]


def _render(request: Request, name: str, user: CurrentUser, **ctx) -> HTMLResponse:
    base = template_context(
        user,
        title=ctx.pop("title", ""),
        active_nav=ctx.pop("active_nav", ""),
    )
    base.update(ctx)
    return TEMPLATES.TemplateResponse(request, name, base)


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    view: Optional[str] = None,
) -> HTMLResponse:
    roles = set(user.role_names)
    # Interesado puro → resumen ejecutivo
    if view is None and "interesado" in roles and "admin" not in roles and "operador_mina" not in roles:
        return RedirectResponse(url="/executive", status_code=302)
    if view is None and "auditor" in roles and not roles.intersection({"admin", "operador_mina", "ingeniero_datos"}):
        return RedirectResponse(url="/audit", status_code=302)

    use_ingeniero = view == "ingeniero" or (
        view is None
        and "ingeniero_datos" in roles
        and "operador_mina" not in roles
        and "admin" not in roles
    )
    if use_ingeniero and ("sensors.manage" in user.permission_codes or "models.train" in user.permission_codes):
        snap = dash_service.ingeniero_snapshot(db)
        return _render(
            request,
            "dashboard/ingeniero.html",
            user,
            title="Panel de datos y modelos",
            active_nav="inicio",
            snapshot=snap,
        )

    sites = dash_service.list_sites(db)
    cards = dash_service.semaforo(db)
    active = dash_service.alertas_activas(db, user_id=user.id, limit=5)
    return _render(
        request,
        "dashboard/operador.html",
        user,
        title="Semáforo operativo",
        active_nav="inicio",
        sites=sites,
        cards=cards,
        alerts=active,
        can_manage_sensors="sensors.manage" in user.permission_codes,
    )


# ---- Sites / sensors (P3) ----
@router.get("/sites", response_class=HTMLResponse)
def sites_list(request: Request, db: DbSession, user: CurrentUser, _: CanPred) -> HTMLResponse:
    return _render(
        request,
        "sites/list.html",
        user,
        title="Sitios y sensores",
        active_nav="sites",
        sites=dash_service.list_sites(db),
    )


@router.get("/sites/{site_id}", response_class=HTMLResponse)
def site_detail(
    site_id: int, request: Request, db: DbSession, user: CurrentUser, _: CanPred
) -> HTMLResponse:
    site = dash_service.get_site(db, site_id)
    cards = dash_service.semaforo(db, site_id=site_id)
    return _render(
        request,
        "sites/detail.html",
        user,
        title=site.name,
        active_nav="sites",
        site={"id": site.id, "name": site.name, "description": site.description},
        cards=cards,
    )


@router.get("/sensors/{sensor_id}", response_class=HTMLResponse)
def sensor_detail(
    sensor_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanPred,
    hours: int = Query(24, ge=1, le=24 * 90),
) -> HTMLResponse:
    sensor = dash_service.get_sensor(db, sensor_id)
    series = dash_service.series_for_sensor(db, sensor_id, hours=hours)
    readings = dash_service.recent_readings(db, sensor_id)
    preds = dash_service.recent_predictions_for_sensor(db, sensor_id)
    return _render(
        request,
        "sites/sensor_detail.html",
        user,
        title=f"Sensor {sensor.code}",
        active_nav="sites",
        series=series,
        readings=readings,
        predictions=preds,
        hours=hours,
    )


# ---- Alerts (P4, P5) ----
@router.get("/alerts", response_class=HTMLResponse)
def alerts_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanAlerts,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    level: Optional[str] = None,
    site_id: Optional[int] = None,
) -> HTMLResponse:
    params = PageParams(page=page, page_size=page_size)
    visible = stake_service.alert_ids_visible_to_user(db, user.id)
    items, total = alerts_service.list_alerts(
        db,
        offset=params.offset,
        limit=params.page_size,
        status=status,
        level=level,
        site_id=site_id,
        visible_ids=visible,
    )
    alerts = [alerts_service.alert_to_dict(db, a) for a in items]
    return _render(
        request,
        "alerts/list.html",
        user,
        title="Bandeja de alertas",
        active_nav="alerts",
        alerts=alerts,
        total=total,
        page=page,
        page_size=page_size,
        status=status or "",
        level=level or "",
        site_id=site_id or "",
        sites=dash_service.list_sites(db),
        can_resolve="alerts.resolve" in user.permission_codes,
    )


@router.get("/alerts/{alert_id}", response_class=HTMLResponse)
def alert_detail_page(
    alert_id: int, request: Request, db: DbSession, user: CurrentUser, _: CanAlerts
) -> HTMLResponse:
    alert = alerts_service.get_alert(db, alert_id)
    if alert is None:
        raise NotFoundError("Alerta no encontrada")
    visible = stake_service.alert_ids_visible_to_user(db, user.id)
    if visible is not None and alert_id not in visible:
        raise PermissionDeniedError("Alerta fuera de tus suscripciones")
    data = alerts_service.alert_to_dict(db, alert)
    notifs = dash_service.notifications_for_alert(db, alert_id)
    return _render(
        request,
        "alerts/detail.html",
        user,
        title=f"Alerta #{alert_id}",
        active_nav="alerts",
        alert=data,
        notifications=notifs,
        can_resolve="alerts.resolve" in user.permission_codes,
    )


# ---- Ingestion (P6) ----
@router.get("/ingestion", response_class=HTMLResponse)
def ingestion_page(request: Request, db: DbSession, user: CurrentUser, _: CanSensors) -> HTMLResponse:
    from app.modules.sensors_ingestion import repository as ingest_repo
    from app.modules.sensors_ingestion import service as ingestion_svc

    items, _total = ingest_repo.list_etl_runs(db, offset=0, limit=30)
    runs = [ingestion_svc.etl_run_to_dict(r) for r in items]
    return _render(
        request,
        "ingestion/panel.html",
        user,
        title="Ingesta / ETL",
        active_nav="ingestion",
        runs=runs,
    )


# ---- ML (P7-P9) ----
@router.get("/ml/models", response_class=HTMLResponse)
def ml_models_page(request: Request, db: DbSession, user: CurrentUser, _: CanTrain) -> HTMLResponse:
    models = ml_service.list_models(db)
    compare = ml_service.compare_models(db)
    return _render(
        request,
        "ml/models.html",
        user,
        title="Catálogo de modelos",
        active_nav="ml",
        models=models,
        compare=compare,
        can_promote="models.promote" in user.permission_codes,
    )


@router.get("/ml/models/{model_id}", response_class=HTMLResponse)
def ml_model_detail(
    model_id: int, request: Request, db: DbSession, user: CurrentUser, _: CanTrain
) -> HTMLResponse:
    model = get_model(db, model_id)
    if model is None:
        raise NotFoundError("Modelo no encontrado")
    data = ml_service._model_to_dict(model)  # noqa: SLF001
    return _render(
        request,
        "ml/model_detail.html",
        user,
        title=f"{data['name']} v{data['version']}",
        active_nav="ml",
        model=data,
        can_promote="models.promote" in user.permission_codes,
    )


@router.get("/ml/train", response_class=HTMLResponse)
def ml_train_page(request: Request, user: CurrentUser, _: CanTrain) -> HTMLResponse:
    return _render(
        request,
        "ml/train.html",
        user,
        title="Nuevo entrenamiento",
        active_nav="ml",
    )


@router.get("/ml/compare", response_class=HTMLResponse)
def ml_compare_page(request: Request, db: DbSession, user: CurrentUser, _: CanTrain) -> HTMLResponse:
    compare = ml_service.compare_models(db)
    return _render(
        request,
        "ml/compare.html",
        user,
        title="Comparativa de modelos",
        active_nav="ml",
        compare=compare,
    )


# ---- Executive / Reports (P10-P11) ----
@router.get("/executive", response_class=HTMLResponse)
def executive_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanAlerts,
    days: int = Query(30, ge=1, le=365),
) -> HTMLResponse:
    kpis = dash_service.executive_kpis(db, days=days, user_id=user.id)
    return _render(
        request,
        "dashboard/ejecutivo.html",
        user,
        title="Resumen ejecutivo",
        active_nav="executive",
        kpis=kpis,
        days=days,
        can_reports="reports.export" in user.permission_codes,
    )


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, db: DbSession, user: CurrentUser, _: CanReports) -> HTMLResponse:
    from app.modules.reports import service as reports_service
    from app.modules.ml_training import service as ml_svc

    items, _ = reports_service.list_reports(db, user, offset=0, limit=50)
    models = []
    if "models.train" in user.permission_codes:
        models = ml_svc.list_models(db)
    return _render(
        request,
        "reports/index.html",
        user,
        title="Reportes",
        active_nav="reports",
        reports=items,
        models=models,
    )


# ---- Stakeholders UI (P12) ----
@router.get("/stakeholders", response_class=HTMLResponse)
def stakeholders_page(request: Request, db: DbSession, user: CurrentUser, _: CanStake) -> HTMLResponse:
    rows = stake_service.list_stakeholders(db)
    items = [stake_service.stakeholder_to_dict(s) for s in rows]
    return _render(
        request,
        "stakeholders/list.html",
        user,
        title="Partes interesadas",
        active_nav="stakeholders",
        stakeholders=items,
        sites=dash_service.list_sites(db),
    )


# ---- Users / Roles (P13) ----
@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: DbSession, user: CurrentUser, _: CanUsers) -> HTMLResponse:
    page = users_service.list_users(db, PageParams(page=1, page_size=100))
    from app.modules.roles_permissions import service as roles_service

    roles = roles_service.list_roles(db)
    return _render(
        request,
        "users/list.html",
        user,
        title="Usuarios",
        active_nav="users",
        users=page.items,
        roles=roles,
    )


@router.get("/roles", response_class=HTMLResponse)
def roles_page(request: Request, db: DbSession, user: CurrentUser, _: CanRoles) -> HTMLResponse:
    from app.modules.roles_permissions import service as roles_service

    roles = roles_service.list_roles(db)
    perms = roles_service.list_permissions(db)
    return _render(
        request,
        "roles/list.html",
        user,
        title="Roles y permisos",
        active_nav="roles",
        roles=roles,
        permissions=perms,
    )


# ---- Audit (P14) ----
@router.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanAudit,
    page: int = Query(1, ge=1),
    action: Optional[str] = None,
) -> HTMLResponse:
    from app.modules.audit import service as audit_service

    items, total = audit_service.list_audit(
        db, offset=(page - 1) * 50, limit=50, action=action
    )
    return _render(
        request,
        "audit/list.html",
        user,
        title="Auditoría",
        active_nav="audit",
        entries=items,
        total=total,
        page=page,
        action=action or "",
    )


# ---- Profile (P15) ----
@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return _render(
        request,
        "profile/index.html",
        user,
        title="Mi perfil",
        active_nav="profile",
        flash=None,
        error=None,
    )


@router.post("/profile/password", response_class=HTMLResponse)
def profile_change_password(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    current_password: str = Form(...),
    new_password: str = Form(...),
) -> HTMLResponse:
    if not verify_password(current_password, user.password_hash):
        return _render(
            request,
            "profile/index.html",
            user,
            title="Mi perfil",
            active_nav="profile",
            flash=None,
            error="La contraseña actual no es correcta",
        )
    if len(new_password) < 8:
        return _render(
            request,
            "profile/index.html",
            user,
            title="Mi perfil",
            active_nav="profile",
            flash=None,
            error="La nueva contraseña debe tener al menos 8 caracteres",
        )
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    return _render(
        request,
        "profile/index.html",
        user,
        title="Mi perfil",
        active_nav="profile",
        flash="Contraseña actualizada",
        error=None,
    )


@router.get("/403", response_class=HTMLResponse)
def forbidden_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return _render(request, "errors/403.html", user, title="Acceso denegado", active_nav="")
