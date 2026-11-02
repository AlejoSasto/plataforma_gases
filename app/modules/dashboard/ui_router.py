"""Vistas HTML en rutas de lenguaje natural (Plan 18)."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.modules.alerts import service as alerts_service
from app.modules.dashboard import service as dash_service
from app.modules.dashboard.nav import template_context
from app.modules.ml_training import service as ml_service
from app.modules.ml_training.repository import get_model
from app.modules.stakeholders import service as stake_service
from app.modules.users import service as users_service
from app.modules.users.models import User
from app.shared import copy
from app.shared import present
from app.shared.dependencies import CurrentUser, DbSession, require_permission
from app.shared.exceptions import NotFoundError, PermissionDeniedError
from app.shared.pagination import PageParams
from app.shared.templating import make_templates

router = APIRouter(tags=["ui"])
TEMPLATES = make_templates()

CanAlerts = Annotated[object, Depends(require_permission("alerts.view"))]
CanResolve = Annotated[object, Depends(require_permission("alerts.resolve"))]
CanSensors = Annotated[object, Depends(require_permission("sensors.manage"))]
CanUpload = Annotated[object, Depends(require_permission("data.upload"))]
CanQuality = Annotated[object, Depends(require_permission("data.quality.view"))]
CanThresholds = Annotated[object, Depends(require_permission("thresholds.manage"))]
CanTrain = Annotated[object, Depends(require_permission("models.train"))]
CanUsers = Annotated[object, Depends(require_permission("users.manage"))]
CanKiosk = Annotated[object, Depends(require_permission("kiosk.manage"))]
CanRoles = Annotated[object, Depends(require_permission("roles.manage"))]
CanStake = Annotated[object, Depends(require_permission("stakeholders.manage"))]
CanAudit = Annotated[object, Depends(require_permission("audit.view"))]
CanReports = Annotated[object, Depends(require_permission("reports.export"))]
CanPred = Annotated[object, Depends(require_permission("predictions.view"))]


def _gone(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=301)


def _render(request: Request, name: str, user: CurrentUser | None, **ctx) -> HTMLResponse:
    base = template_context(
        user,
        title=ctx.pop("title", ""),
        active_nav=ctx.pop("active_nav", ""),
    ) if user is not None else {"current_user": None, "permissions": set(), "roles": set(), "title": ctx.pop("title", ""), "active_nav": ""}
    base.update(ctx)
    base.setdefault("sala", False)
    return TEMPLATES.TemplateResponse(request, name, base)


def _hoy_context(db, user: CurrentUser, *, site_ids: list[int] | None = None, skip_scope: bool = False) -> dict:
    from app.shared.access import scoped_site_ids, user_has_permission

    sites = dash_service.list_sites(db, user=None if skip_scope else user)
    if site_ids:
        sites = [s for s in sites if s["id"] in set(site_ids)]
    raw_cards = dash_service.semaforo(db, user=None if skip_scope else user)
    if site_ids:
        allowed = set(site_ids)
        raw_cards = [c for c in raw_cards if c.get("site_id") in allowed]
    cards = [present.present_card(c) for c in raw_cards]
    n_att = present.attention_count(raw_cards)
    banner = copy.banner_summary(n_att)
    banner_level = "normal"
    keys = [c["status_key"] for c in cards]
    if "evacuar" in keys:
        banner_level = "evacuar"
    elif "actuar" in keys:
        banner_level = "actuar"
    elif "vigilar" in keys:
        banner_level = "vigilar"
    scope = None if skip_scope else scoped_site_ids(db, user)
    if scope is not None and not scope:
        banner = "No tienes zonas asignadas. Pide a quien administra el equipo que te asigne una."
        banner_level = "sin_datos"
    active = dash_service.alertas_activas(db, user_id=user.id, limit=5)
    alerts = [present.present_alert(a) for a in active]
    spec = present.load_spec()
    horizon = spec.horizons[0] if spec.horizons else 6
    chart_payload = None
    if raw_cards:
        try:
            chart_payload = present.chart_now_and_next(db, int(raw_cards[0]["sensor_id"]))
        except Exception:  # noqa: BLE001
            chart_payload = None
    return {
        "sites": sites,
        "cards": cards,
        "alerts": alerts,
        "banner": banner,
        "banner_level": banner_level,
        "horizon": horizon,
        "grid_seconds": max(30, present.grid_step_minutes(db) * 60),
        "chart_payload": chart_payload,
        "can_manage_sensors": (not skip_scope) and user_has_permission(user, "data.upload"),
        "can_resolve": (not skip_scope) and user_has_permission(user, "alerts.resolve"),
    }


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    view: Optional[str] = None,
) -> HTMLResponse:
    from app.shared.access import canonical_role, user_has_permission

    roles = {canonical_role(r) for r in user.role_names}
    if view is None and "gerencia" in roles and not roles.intersection({"admin", "operador", "supervisor_seguridad"}):
        return RedirectResponse(url="/resumen", status_code=302)
    if view is None and "auditor" in roles and not roles.intersection({"admin", "operador", "analista"}):
        return RedirectResponse(url="/bitacora", status_code=302)

    use_ingeniero = view == "ingeniero" or (
        view is None
        and "analista" in roles
        and "operador" not in roles
        and "admin" not in roles
    )
    if use_ingeniero and (user_has_permission(user, "data.upload") or user_has_permission(user, "models.train")):
        snap = dash_service.ingeniero_snapshot(db)
        return _render(
            request,
            "dashboard/ingeniero.html",
            user,
            title="Datos y laboratorio",
            active_nav="laboratorio",
            snapshot=snap,
        )

    ctx = _hoy_context(db, user)
    return _render(request, "dashboard/hoy.html", user, title="Hoy", active_nav="hoy", **ctx)


@router.get("/fragmentos/hoy", response_class=HTMLResponse)
def hoy_fragment(request: Request, db: DbSession, user: CurrentUser) -> HTMLResponse:
    ctx = _hoy_context(db, user)
    return _render(request, "dashboard/_hoy_inner.html", user, title="Hoy", active_nav="hoy", **ctx)


# ---- Zonas / sensores ----
@router.get("/zonas", response_class=HTMLResponse)
def zonas_list(request: Request, db: DbSession, user: CurrentUser, _: CanPred) -> HTMLResponse:
    return _render(
        request,
        "sites/list.html",
        user,
        title="Zonas y sensores",
        active_nav="zonas",
        sites=dash_service.list_sites(db, user=user),
    )


@router.get("/zonas/{site_id}", response_class=HTMLResponse)
def zona_detail(site_id: int, request: Request, db: DbSession, user: CurrentUser, _: CanPred) -> HTMLResponse:
    site = dash_service.get_site(db, site_id)
    from app.shared.access import site_allowed

    if not site_allowed(db, user, site_id):
        raise PermissionDeniedError("Zona fuera de tu alcance")
    cards = [present.present_card(c) for c in dash_service.semaforo(db, site_id=site_id, user=user)]
    return _render(
        request,
        "sites/detail.html",
        user,
        title=site.name,
        active_nav="zonas",
        site={"id": site.id, "name": site.name, "description": site.description},
        cards=cards,
    )


@router.get("/sensores/{sensor_id}", response_class=HTMLResponse)
def sensor_detail(
    sensor_id: int,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanPred,
    hours: int = Query(24, ge=1, le=24 * 90),
) -> HTMLResponse:
    from app.shared.access import site_allowed

    sensor = dash_service.get_sensor(db, sensor_id)
    if not site_allowed(db, user, sensor.site_id):
        raise PermissionDeniedError("Zona fuera de tu alcance")
    series = dash_service.series_for_sensor(db, sensor_id, hours=hours)
    readings = dash_service.recent_readings(db, sensor_id)
    forecasts = dash_service.recent_forecasts_for_sensor(db, sensor_id)
    cards = dash_service.semaforo(db, site_id=sensor.site_id, user=user)
    this = next((c for c in cards if c["sensor_id"] == sensor_id), None)
    presented = present.present_card(this) if this else present.present_card({"sensor_id": sensor_id, "risk_level": "sin_datos"})
    chart_payload = present.chart_now_and_next(db, sensor_id, hours=float(hours))
    reading_rows = [[r.get("tiempo_inicio") or "—", r.get("leyendo") or "—"] for r in readings]
    last_fc = forecasts[0] if forecasts else None
    confidence = copy.confidence_phrase(last_fc.get("confidence") if last_fc else None)
    return _render(
        request,
        "sites/sensor_detail.html",
        user,
        title=f"Sensor {sensor.code}",
        active_nav="zonas",
        series=series,
        readings=readings,
        forecasts=forecasts,
        hours=hours,
        status_key=presented["status_key"],
        chart_payload=chart_payload,
        reading_rows=reading_rows,
        confidence=confidence,
        has_forecast=bool(forecasts),
    )


# ---- Avisos ----
@router.get("/avisos", response_class=HTMLResponse)
def avisos_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanAlerts,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = "abierta",
    level: Optional[str] = None,
    site_id: Optional[int] = None,
) -> HTMLResponse:
    from app.shared.access import scoped_site_ids

    params = PageParams(page=page, page_size=page_size)
    visible = stake_service.alert_ids_visible_to_user(db, user.id)
    scope = scoped_site_ids(db, user)
    items, total = alerts_service.list_alerts(
        db,
        offset=params.offset,
        limit=params.page_size,
        status=status or None,
        level=level,
        site_id=site_id,
        site_ids=scope,
        visible_ids=visible,
    )
    alerts = [present.present_alert(alerts_service.alert_to_dict(db, a)) for a in items]
    return _render(
        request,
        "alerts/list.html",
        user,
        title="Avisos",
        active_nav="avisos",
        alerts=alerts,
        total=total,
        page=page,
        page_size=page_size,
        status=status or "abierta",
        level=level or "",
        site_id=site_id or "",
        sites=dash_service.list_sites(db, user=user),
        can_resolve="alerts.resolve" in user.permission_codes,
    )


@router.get("/avisos/{alert_id}", response_class=HTMLResponse)
def aviso_detalle(
    alert_id: int, request: Request, db: DbSession, user: CurrentUser, _: CanAlerts
) -> HTMLResponse:
    alert = alerts_service.get_alert(db, alert_id)
    if alert is None:
        raise NotFoundError("Aviso no encontrado")
    visible = stake_service.alert_ids_visible_to_user(db, user.id)
    if visible is not None and alert_id not in visible:
        raise PermissionDeniedError("Aviso fuera de tus suscripciones")
    data = present.present_alert(alerts_service.alert_to_dict(db, alert))
    chart_payload = present.chart_now_and_next(db, alert.sensor_id)
    return _render(
        request,
        "alerts/detail.html",
        user,
        title="Aviso",
        active_nav="avisos",
        alert=data,
        chart_payload=chart_payload,
        can_resolve="alerts.resolve" in user.permission_codes,
    )


@router.get("/historial", response_class=HTMLResponse)
def historial_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanPred,
    site_id: Optional[int] = None,
    hours: int = Query(24, ge=1, le=24 * 90),
) -> HTMLResponse:
    chart_payload = None
    if site_id:
        cards = dash_service.semaforo(db, site_id=site_id)
        if cards:
            chart_payload = present.chart_now_and_next(db, int(cards[0]["sensor_id"]), hours=float(hours))
    return _render(
        request,
        "historial.html",
        user,
        title="Historial",
        active_nav="historial",
        sites=dash_service.list_sites(db, user=user),
        site_id=site_id or "",
        hours=hours,
        chart_payload=chart_payload,
    )


@router.get("/informes", response_class=HTMLResponse)
def informes_page(request: Request, db: DbSession, user: CurrentUser, _: CanReports) -> HTMLResponse:
    from app.modules.reports import service as reports_service

    items, _ = reports_service.list_reports(db, user, offset=0, limit=50)
    models = []
    if "models.train" in user.permission_codes:
        models = ml_service.list_models(db)
    type_label = {
        "alertas": "Avisos del periodo",
        "ejecutivo": "Resumen para gerencia",
        "modelo": "Confiabilidad del sistema",
    }
    report_rows = [
        [
            type_label.get(r.get("type"), r.get("type")),
            f"{r.get('period_start') or '—'} → {r.get('period_end') or '—'}",
            r.get("created_at") or "",
            f"<a href='{r.get('download_url')}'>Descargar</a>" if r.get("download_url") else "",
        ]
        for r in items
    ]
    return _render(
        request,
        "reports/index.html",
        user,
        title="Informes",
        active_nav="informes",
        reports=items,
        models=models,
        report_rows=report_rows,
    )


@router.get("/confiabilidad", response_class=HTMLResponse)
def confiabilidad_page(request: Request, db: DbSession, user: CurrentUser) -> HTMLResponse:
    if not (
        "reports.export" in user.permission_codes
        or "audit.view" in user.permission_codes
        or "admin" in user.role_names
    ):
        raise PermissionDeniedError("Sin acceso a confiabilidad")
    snap = present.reliability_snapshot(db)
    return _render(
        request,
        "dashboard/confiabilidad.html",
        user,
        title="Confiabilidad",
        active_nav="confiabilidad",
        snap=snap,
        g0=present.g0_context(),
    )


@router.get("/resumen", response_class=HTMLResponse)
def resumen_page(
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
        title="Resumen para gerencia",
        active_nav="resumen",
        kpis=kpis,
        days=days,
        can_reports="reports.export" in user.permission_codes,
    )


@router.get("/datos/cargar", response_class=HTMLResponse)
def cargar_datos(request: Request, db: DbSession, user: CurrentUser, _: CanUpload) -> HTMLResponse:
    from app.modules.sensors_ingestion import repository as ingest_repo
    from app.modules.sensors_ingestion import service as ingestion_svc
    from app.shared.formatting import format_datetime_short

    items, _total = ingest_repo.list_etl_runs(db, offset=0, limit=30)
    runs = []
    for r in items:
        d = ingestion_svc.etl_run_to_dict(r)
        d["started_at"] = format_datetime_short(d.get("started_at"))
        d["finished_at"] = format_datetime_short(d.get("finished_at"))
        runs.append(d)
    stages = {f"E{i}": copy.stage_label(f"E{i}") for i in range(1, 7)}
    return _render(
        request,
        "ingestion/panel.html",
        user,
        title="Cargar datos",
        active_nav="cargar",
        runs=runs,
        stages=stages,
    )


@router.get("/datos/calidad", response_class=HTMLResponse)
def calidad_datos(request: Request, db: DbSession, user: CurrentUser, _: CanQuality) -> HTMLResponse:
    quality = present.data_quality(db)
    coverage_rows = [[c["sensor"], c["readings_24h"]] for c in quality["coverage"]]
    issue_rows = [[i["code"], i["severity"], i["when"] or ""] for i in quality["issues"]]
    return _render(
        request,
        "datos/calidad.html",
        user,
        title="Calidad de los datos",
        active_nav="calidad",
        quality=quality,
        coverage_rows=coverage_rows,
        issue_rows=issue_rows,
    )


@router.get("/ajustes/limites", response_class=HTMLResponse)
def ajustes_limites(request: Request, db: DbSession, user: CurrentUser, _: CanThresholds) -> HTMLResponse:
    return _render(
        request,
        "ajustes/limites.html",
        user,
        title="Límites",
        active_nav="ajustes",
        limits=present.list_limits(db),
    )


@router.get("/laboratorio", response_class=HTMLResponse)
def laboratorio_zoo(request: Request, db: DbSession, user: CurrentUser, _: CanTrain) -> HTMLResponse:
    models = ml_service.list_models(db)
    compare = ml_service.compare_models(db)
    return _render(
        request,
        "laboratorio/zoo.html",
        user,
        title="Laboratorio",
        active_nav="laboratorio",
        models=models,
        compare=compare,
        can_promote="models.promote" in user.permission_codes,
    )


@router.get("/laboratorio/modelos/{model_id}", response_class=HTMLResponse)
def laboratorio_detalle(
    model_id: int, request: Request, db: DbSession, user: CurrentUser, _: CanTrain
) -> HTMLResponse:
    model = get_model(db, model_id)
    if model is None:
        raise NotFoundError("Modelo no encontrado")
    data = ml_service._model_to_dict(model)  # noqa: SLF001
    return _render(
        request,
        "laboratorio/detalle.html",
        user,
        title=f"{data['name']} v{data['version']}",
        active_nav="laboratorio",
        model=data,
        can_promote="models.promote" in user.permission_codes,
    )


@router.get("/laboratorio/entrenar", response_class=HTMLResponse)
def laboratorio_entrenar(request: Request, user: CurrentUser, _: CanTrain) -> HTMLResponse:
    return _render(request, "laboratorio/entrenar.html", user, title="Entrenar", active_nav="laboratorio")


@router.get("/laboratorio/comparar", response_class=HTMLResponse)
def laboratorio_comparar(request: Request, db: DbSession, user: CurrentUser, _: CanTrain) -> HTMLResponse:
    compare = ml_service.compare_models(db)
    return _render(
        request, "laboratorio/comparar.html", user, title="Comparativa", active_nav="laboratorio", compare=compare
    )


@router.get("/contactos", response_class=HTMLResponse)
def contactos_page(request: Request, db: DbSession, user: CurrentUser, _: CanStake) -> HTMLResponse:
    rows = stake_service.list_stakeholders(db)
    items = [stake_service.stakeholder_to_dict(s) for s in rows]
    return _render(
        request,
        "stakeholders/list.html",
        user,
        title="Contactos de aviso",
        active_nav="contactos",
        stakeholders=items,
        sites=dash_service.list_sites(db, user=user),
    )


@router.get("/equipo", response_class=HTMLResponse)
def equipo_page(request: Request, db: DbSession, user: CurrentUser, _: CanUsers) -> HTMLResponse:
    from app.modules.roles_permissions import service as roles_service
    from app.shared.access import ROLE_LABELS, role_label
    from app.shared.formatting import format_datetime_short

    page = users_service.list_users(db, PageParams(page=1, page_size=100))
    roles = roles_service.list_roles(db)
    for r in roles:
        r["label"] = ROLE_LABELS.get(r["name"], r["name"])
    sites = dash_service.list_sites(db)
    site_names = {s["id"]: s["name"] for s in sites}
    people = []
    for u in page.items:
        item = dict(u)
        item["role_labels"] = ", ".join(role_label(n) for n in (u.get("roles") or []))
        sids = u.get("site_ids") or []
        item["site_label"] = ", ".join(site_names.get(i, str(i)) for i in sids) or "—"
        item["last_login_label"] = format_datetime_short(u.get("last_login_at")) or "Nunca"
        people.append(item)
    return _render(
        request,
        "users/list.html",
        user,
        title="Equipo",
        active_nav="equipo",
        users=people,
        roles=roles,
        sites=sites,
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
        active_nav="equipo",
        roles=roles,
        perm_catalog=perms,
    )


@router.get("/bitacora", response_class=HTMLResponse)
def bitacora_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    _: CanAudit,
    page: int = Query(1, ge=1),
    action: Optional[str] = None,
) -> HTMLResponse:
    from app.modules.audit import service as audit_service

    items, total = audit_service.list_audit(db, offset=(page - 1) * 50, limit=50, action=action)
    names: dict[int, str] = {}
    for e in items:
        uid = e.get("user_id")
        if uid and uid not in names:
            u = db.query(User).filter(User.id == uid).first()
            names[uid] = u.full_name if u else "Alguien"
        who = names.get(e.get("user_id") or 0, "Alguien")
        e["phrase"] = copy.audit_phrase(
            who, e.get("action") or "", e.get("created_at") or "", e.get("details")
        )
    return _render(
        request,
        "audit/list.html",
        user,
        title="Bitácora",
        active_nav="bitacora",
        entries=items,
        total=total,
        page=page,
        action=action or "",
    )


def _cuenta_ctx(user: CurrentUser) -> dict:
    from app.shared.access import TOTP_REQUIRED_ROLES, canonical_role, role_label

    roles = {canonical_role(r) for r in user.role_names}
    return {
        "role_labels": [role_label(canonical_role(r)) for r in user.role_names],
        "totp_on": bool(user.totp_enabled),
        "totp_required": bool(roles & TOTP_REQUIRED_ROLES and not user.totp_enabled),
    }


@router.get("/mi-cuenta", response_class=HTMLResponse)
def mi_cuenta(request: Request, user: CurrentUser) -> HTMLResponse:
    return _render(
        request, "profile/index.html", user, title="Mi cuenta", active_nav="cuenta",
        flash=None, error=None, **_cuenta_ctx(user),
    )


@router.post("/mi-cuenta/contrasena", response_class=HTMLResponse)
def mi_cuenta_password(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    current_password: str = Form(...),
    new_password: str = Form(...),
) -> HTMLResponse:
    if not verify_password(current_password, user.password_hash):
        return _render(
            request, "profile/index.html", user, title="Mi cuenta", active_nav="cuenta",
            flash=None, error="La contraseña actual no es correcta", **_cuenta_ctx(user),
        )
    from app.modules.auth import service as auth_svc
    from app.shared.exceptions import ValidationError as VErr

    try:
        auth_svc.change_password(db, user=user, current=current_password, new=new_password)
    except VErr as exc:
        return _render(
            request, "profile/index.html", user, title="Mi cuenta", active_nav="cuenta",
            flash=None, error=exc.message, **_cuenta_ctx(user),
        )
    return _render(
        request, "profile/index.html", user, title="Mi cuenta", active_nav="cuenta",
        flash="Contraseña actualizada", error=None, **_cuenta_ctx(user),
    )


@router.get("/pantallas", response_class=HTMLResponse)
def pantallas_page(request: Request, db: DbSession, user: CurrentUser, _: CanKiosk) -> HTMLResponse:
    from datetime import datetime, timedelta, timezone

    from app.modules.auth import kiosk as kiosk_svc
    from app.shared.formatting import format_datetime_short

    now = datetime.now(timezone.utc)
    devices = []
    for d in kiosk_svc.list_devices(db):
        last = d.last_seen_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        stale = last is not None and (now - last) > timedelta(minutes=5) and d.revoked_at is None
        devices.append(
            {
                "id": d.id,
                "name": d.name,
                "revoked": d.revoked_at is not None,
                "last_seen_label": format_datetime_short(d.last_seen_at) or "Aún no se abre",
                "stale": stale,
            }
        )
    return _render(
        request,
        "kiosk/list.html",
        user,
        title="Pantallas de sala",
        active_nav="pantallas",
        devices=devices,
        sites=dash_service.list_sites(db),
    )


@router.get("/sala", response_class=HTMLResponse)
def sala_page(request: Request, db: DbSession) -> HTMLResponse:
    from app.modules.auth import kiosk as kiosk_svc
    from app.shared.dependencies import get_current_user

    raw = request.query_params.get("kiosk") or request.cookies.get(kiosk_svc.KIOSK_COOKIE)
    device = kiosk_svc.get_active(db, raw)
    user = None
    site_ids = None
    if device is None:
        user = get_current_user(request, db)
    else:
        site_ids = list(device.site_ids or [])
    if user is None and device is None:
        raise PermissionDeniedError("Esta pantalla no está emparejada")
    if user is not None:
        ctx = _hoy_context(db, user)
    else:
        class _KioskUser:
            id = 0
            permission_codes = ["status.view", "alerts.view"]
            role_names = ["operador"]
            full_name = device.name if device else "Sala"
            email = ""

        ctx = _hoy_context(
            db, _KioskUser(), site_ids=site_ids or None, skip_scope=True  # type: ignore[arg-type]
        )
        ctx["current_user"] = None
    ctx["sala"] = True
    response = _render(request, "sala.html", user, title="Sala de control", active_nav="", **ctx)
    if raw and device is not None:
        response.set_cookie(kiosk_svc.KIOSK_COOKIE, raw, httponly=True, samesite="lax", path="/sala")
    return response


@router.get("/_componentes", response_class=HTMLResponse)
def componentes_page(
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> HTMLResponse:
    if settings.environment != "local":
        raise NotFoundError("No encontrado")
    # Solo datos reales del último periodo (o vacío). Sin cifras inventadas del kit.
    sample_alert = None
    active = dash_service.alertas_activas(db, user_id=user.id, limit=1)
    if active:
        sample_alert = present.present_alert(active[0])
    sample_chart = None
    cards = dash_service.semaforo(db, user=user)
    if cards:
        try:
            sample_chart = present.chart_now_and_next(db, int(cards[0]["sensor_id"]))
        except Exception:  # noqa: BLE001
            sample_chart = None
    return _render(
        request,
        "_componentes.html",
        user,
        title="Componentes",
        active_nav="",
        sample_alert=sample_alert,
        sample_chart=sample_chart,
    )


@router.get("/403", response_class=HTMLResponse)
def forbidden_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return _render(request, "errors/403.html", user, title="Acceso denegado", active_nav="")


# ---- Compatibilidad 301 ----
@router.get("/sites")
def old_sites() -> RedirectResponse:
    return _gone("/zonas")


@router.get("/sites/{site_id}")
def old_site(site_id: int) -> RedirectResponse:
    return _gone(f"/zonas/{site_id}")


@router.get("/sensors/{sensor_id}")
def old_sensor(sensor_id: int) -> RedirectResponse:
    return _gone(f"/sensores/{sensor_id}")


@router.get("/alerts")
def old_alerts() -> RedirectResponse:
    return _gone("/avisos")


@router.get("/alerts/{alert_id}")
def old_alert(alert_id: int) -> RedirectResponse:
    return _gone(f"/avisos/{alert_id}")


@router.get("/ingestion")
def old_ingestion() -> RedirectResponse:
    return _gone("/datos/cargar")


@router.get("/ml/models")
def old_ml() -> RedirectResponse:
    return _gone("/laboratorio")


@router.get("/ml/models/{model_id}")
def old_ml_detail(model_id: int) -> RedirectResponse:
    return _gone(f"/laboratorio/modelos/{model_id}")


@router.get("/ml/train")
def old_ml_train() -> RedirectResponse:
    return _gone("/laboratorio/entrenar")


@router.get("/ml/compare")
def old_ml_compare() -> RedirectResponse:
    return _gone("/laboratorio/comparar")


@router.get("/executive")
def old_executive() -> RedirectResponse:
    return _gone("/resumen")


@router.get("/reports")
def old_reports() -> RedirectResponse:
    return _gone("/informes")


@router.get("/stakeholders")
def old_stakeholders() -> RedirectResponse:
    return _gone("/contactos")


@router.get("/users")
def old_users() -> RedirectResponse:
    return _gone("/equipo")


@router.get("/audit")
def old_audit() -> RedirectResponse:
    return _gone("/bitacora")


@router.get("/profile")
def old_profile() -> RedirectResponse:
    return _gone("/mi-cuenta")


@router.post("/profile/password", response_class=HTMLResponse)
def old_profile_password(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    current_password: str = Form(...),
    new_password: str = Form(...),
) -> HTMLResponse:
    return mi_cuenta_password(request, db, user, current_password, new_password)
