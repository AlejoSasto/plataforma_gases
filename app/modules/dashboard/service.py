"""Servicios de datos para el dashboard (semáforo, series, KPIs)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.alerts import service as alerts_service
from app.modules.forecasting.models import Forecast
from app.modules.forecasting import repository as forecast_repo
from app.modules.ml_training.models import ModelRegistry, TrainingJob
from app.modules.sensors_ingestion.models import EtlRun, GasReading, Sensor, Site
from app.modules.stakeholders.models import AlertNotification
from app.modules.stakeholders.service import alert_ids_visible_to_user
from app.shared.exceptions import NotFoundError
from app.shared.formatting import (
    display_gas,
    display_sensor_code,
    display_site_name,
    format_datetime_short,
    format_reading_value,
)
from app.shared.gas_catalog import canonicalize_gas_type, thesis_priority_gases

LEVEL_RANK = {"NORMAL": 0, "PRECAUCION": 1, "ALERTA": 2, "CRITICO": 3}


def list_sites(db: Session, user=None) -> list[dict[str, Any]]:
    from app.shared.access import scoped_site_ids

    sites = db.query(Site).order_by(Site.name.asc()).all()
    scope = scoped_site_ids(db, user) if user is not None else None
    return [
        {
            "id": s.id,
            "name": display_site_name(s.name),
            "description": s.description,
            "sensors_count": len(s.sensors or []),
        }
        for s in sites
        if scope is None or s.id in scope
    ]


def get_site(db: Session, site_id: int) -> Site:
    site = db.query(Site).filter(Site.id == site_id).first()
    if site is None:
        raise NotFoundError("Sitio no encontrado")
    return site


def get_sensor(db: Session, sensor_id: int) -> Sensor:
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if sensor is None:
        raise NotFoundError("Sensor no encontrado")
    return sensor


def semaforo(db: Session, *, site_id: Optional[int] = None, user=None) -> list[dict[str, Any]]:
    from app.shared.access import scoped_site_ids

    q = db.query(Sensor, Site).join(Site, Sensor.site_id == Site.id)
    if site_id is not None:
        q = q.filter(Sensor.site_id == site_id)
    scope = scoped_site_ids(db, user) if user is not None else None
    if scope is not None:
        q = q.filter(Sensor.site_id.in_(scope or {-1}))
    rows = q.order_by(Site.name.asc(), Sensor.code.asc()).all()
    result: list[dict[str, Any]] = []
    for sensor, site in rows:
        last_reading = (
            db.query(GasReading)
            .filter(GasReading.sensor_id == sensor.id)
            .order_by(GasReading.tiempo_inicio.desc())
            .first()
        )
        last_fc = forecast_repo.latest_for_sensor(db, sensor.id)
        open_alert = (
            db.query(Alert)
            .filter(
                Alert.sensor_id == sensor.id,
                Alert.status.in_(["abierta", "reconocida"]),
            )
            .order_by(Alert.created_at.desc())
            .first()
        )
        risk = "NORMAL"
        if open_alert is not None:
            risk = open_alert.level
        elif last_fc is not None and last_fc.status_level:
            risk = last_fc.status_level.upper() if last_fc.status_level in {"vigilar", "actuar", "evacuar", "normal"} else last_fc.status_level
        result.append(
            {
                "sensor_id": sensor.id,
                "sensor_code": display_sensor_code(sensor.code),
                "gas_type": display_gas(sensor.gas_type),
                "gas_code": canonicalize_gas_type(sensor.gas_type),
                "unit": sensor.unit,
                "site_id": site.id,
                "site_name": display_site_name(site.name),
                "risk_level": risk,
                "last_value": format_reading_value(last_reading.leyendo)
                if last_reading
                else None,
                "last_at": format_datetime_short(last_reading.tiempo_inicio)
                if last_reading
                else None,
                "probability": None,
                "predicted_concentration": forecast_repo.q50_for(last_fc) if last_fc else None,
                "horizon_minutes": None,
                "open_alert_id": open_alert.id if open_alert else None,
            }
        )
    return result


def series_for_sensor(
    db: Session,
    sensor_id: int,
    *,
    hours: int = 24,
) -> dict[str, Any]:
    from app.modules.forecasting.service import reference_time

    sensor = get_sensor(db, sensor_id)
    site = db.query(Site).filter(Site.id == sensor.site_id).first()
    ref = reference_time(db, sensor_id)
    since = ref - timedelta(hours=hours)
    readings = (
        db.query(GasReading)
        .filter(
            GasReading.sensor_id == sensor_id,
            GasReading.tiempo_inicio >= since,
            GasReading.tiempo_inicio <= ref,
        )
        .order_by(GasReading.tiempo_inicio.asc())
        .limit(2000)
        .all()
    )
    points = [
        {
            "t": r.tiempo_inicio.isoformat(),
            "leyendo": r.leyendo,
            "stel_max": r.stel_max,
            "twa_max": r.twa_max,
        }
        for r in readings
    ]
    last = readings[-1] if readings else None
    return {
        "sensor_id": sensor.id,
        "sensor_code": display_sensor_code(sensor.code),
        "gas_type": display_gas(sensor.gas_type),
        "unit": sensor.unit,
        "site_id": sensor.site_id,
        "site_name": display_site_name(site.name) if site else None,
        "hours": hours,
        "points": points,
        "stel_max": last.stel_max if last else None,
        "twa_max": last.twa_max if last else None,
        "reference_time": ref.isoformat(),
        "data_until": ref.isoformat(),
    }


def forecast_by_gas(
    db: Session,
    *,
    site_id: Optional[int] = None,
    hours: int = 6,
    horizon_minutes: float = 7.5,
) -> dict[str, Any]:
    """Series históricas + proyección de concentración agrupadas por gas canónico."""
    from app.modules.forecasting.service import reference_time

    ref = reference_time(db, None)
    since = ref - timedelta(hours=hours)
    priority = thesis_priority_gases()
    forecast_available = db.query(Forecast.id).first() is not None

    q = (
        db.query(GasReading, Sensor)
        .join(Sensor, Sensor.id == GasReading.sensor_id)
        .filter(
            GasReading.tiempo_inicio >= since,
            GasReading.tiempo_inicio <= ref,
            GasReading.is_synthetic.is_(False),
        )
    )
    if site_id is not None:
        q = q.filter(Sensor.site_id == site_id)
    rows = q.order_by(GasReading.tiempo_inicio.asc()).limit(8000).all()

    # bucket: gas_code -> minute_iso -> list values
    hist_buckets: dict[str, dict[str, list[float]]] = {g: {} for g in priority}
    last_by_sensor: dict[int, GasReading] = {}
    sensors_by_gas: dict[str, set[int]] = {g: set() for g in priority}

    for reading, sensor in rows:
        code = canonicalize_gas_type(sensor.gas_type)
        if code not in hist_buckets:
            hist_buckets[code] = {}
            sensors_by_gas.setdefault(code, set())
        sensors_by_gas[code].add(sensor.id)
        minute_key = reading.tiempo_inicio.replace(second=0, microsecond=0).isoformat()
        hist_buckets[code].setdefault(minute_key, []).append(float(reading.leyendo))
        prev = last_by_sensor.get(sensor.id)
        if prev is None or reading.tiempo_inicio >= prev.tiempo_inicio:
            last_by_sensor[sensor.id] = reading

    # Fallback: gases thesis sin datos en la ventana → últimas lecturas
    for code in priority:
        if hist_buckets.get(code):
            continue
        sq = (
            db.query(GasReading, Sensor)
            .join(Sensor, Sensor.id == GasReading.sensor_id)
            .filter(
                GasReading.is_synthetic.is_(False),
                Sensor.gas_type == code,
            )
        )
        if site_id is not None:
            sq = sq.filter(Sensor.site_id == site_id)
        fallback = sq.order_by(GasReading.tiempo_inicio.desc()).limit(200).all()
        for reading, sensor in reversed(fallback):
            sensors_by_gas.setdefault(code, set()).add(sensor.id)
            minute_key = reading.tiempo_inicio.replace(second=0, microsecond=0).isoformat()
            hist_buckets.setdefault(code, {})
            hist_buckets[code].setdefault(minute_key, []).append(float(reading.leyendo))
            prev = last_by_sensor.get(sensor.id)
            if prev is None or reading.tiempo_inicio >= prev.tiempo_inicio:
                last_by_sensor[sensor.id] = reading

    gases_payload: list[dict[str, Any]] = []

    gas_codes = list(priority)
    for code in hist_buckets:
        if code not in gas_codes:
            gas_codes.append(code)

    for code in gas_codes:
        buckets = hist_buckets.get(code) or {}
        historical = []
        for t_key in sorted(buckets.keys()):
            vals = buckets[t_key]
            if not vals:
                continue
            historical.append(
                {
                    "t": t_key,
                    "t_label": format_datetime_short(t_key),
                    "value": round(sum(vals) / len(vals), 4),
                }
            )

        forecast_points: list[dict[str, Any]] = []
        if forecast_available:
            sensor_ids = sensors_by_gas.get(code) or set()
            concs: list[float] = []
            base_ts = None
            h = horizon_minutes
            for sid in sensor_ids:
                fc = forecast_repo.latest_for_sensor(db, sid)
                if fc is None:
                    continue
                conc = forecast_repo.q50_for(fc)
                if conc is not None:
                    concs.append(float(conc))
                    if base_ts is None or fc.issued_at > base_ts:
                        base_ts = fc.issued_at
            if concs and base_ts is not None:
                avg_conc = sum(concs) / len(concs)
                last_real = historical[-1]["value"] if historical else avg_conc
                last_t = (
                    datetime.fromisoformat(historical[-1]["t"].replace("Z", "+00:00"))
                    if historical
                    else base_ts
                )
                if last_t.tzinfo is None:
                    last_t = last_t.replace(tzinfo=timezone.utc)
                future_t = last_t + timedelta(minutes=float(h))
                forecast_points = [
                    {
                        "t": last_t.isoformat(),
                        "t_label": format_datetime_short(last_t),
                        "value": round(float(last_real), 4),
                    },
                    {
                        "t": future_t.isoformat(),
                        "t_label": format_datetime_short(future_t),
                        "value": round(float(avg_conc), 4),
                    },
                ]

        gases_payload.append(
            {
                "gas_code": code,
                "gas_label": display_gas(code),
                "unit": None,
                "sensors_count": len(sensors_by_gas.get(code) or []),
                "historical": historical,
                "forecast": forecast_points,
            }
        )

    # Solo gases con datos o prioritarios
    gases_payload = [
        g
        for g in gases_payload
        if g["historical"] or g["forecast"] or g["gas_code"] in priority
    ]

    return {
        "hours": hours,
        "horizon_minutes": horizon_minutes,
        "site_id": site_id,
        "forecast_available": forecast_available,
        "reference_time": ref.isoformat(),
        "data_until": ref.isoformat(),
        "updated_at": ref.isoformat(),
        "gases": gases_payload,
    }


def alertas_activas(
    db: Session,
    *,
    user_id: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    visible = alert_ids_visible_to_user(db, user_id)
    items, _ = alerts_service.list_alerts(
        db,
        offset=0,
        limit=limit,
        status=None,
        level=None,
        site_id=None,
        visible_ids=visible,
    )
    # Prefer open/recognized
    filtered = [a for a in items if a.status in ("abierta", "reconocida")]
    if not filtered:
        filtered = items
    return [alerts_service.alert_to_dict(db, a) for a in filtered[:limit]]


def executive_kpis(db: Session, *, days: int = 30, user_id: Optional[int] = None) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    visible = alert_ids_visible_to_user(db, user_id) if user_id else None
    q = db.query(Alert).filter(Alert.created_at >= since)
    if visible is not None:
        if not visible:
            return {
                "days": days,
                "by_level": {},
                "total": 0,
                "avg_resolution_hours": None,
                "top_site": None,
                "trend": [],
            }
        q = q.filter(Alert.id.in_(visible))
    alerts = q.all()
    by_level: dict[str, int] = {}
    for a in alerts:
        by_level[a.level] = by_level.get(a.level, 0) + 1

    resolved = [a for a in alerts if a.resolved_at is not None]
    avg_hours = None
    if resolved:
        deltas = [
            (a.resolved_at - a.created_at).total_seconds() / 3600.0
            for a in resolved
            if a.resolved_at and a.created_at
        ]
        if deltas:
            avg_hours = round(sum(deltas) / len(deltas), 2)

    site_counts: dict[str, int] = {}
    for a in alerts:
        d = alerts_service.alert_to_dict(db, a)
        name = d.get("site_name") or "N/D"
        site_counts[name] = site_counts.get(name, 0) + 1
    top_site = None
    if site_counts:
        top_site = max(site_counts.items(), key=lambda x: x[1])

    # trend by day
    day_counts: dict[str, int] = {}
    for a in alerts:
        key = a.created_at.date().isoformat()
        day_counts[key] = day_counts.get(key, 0) + 1
    trend = [{"date": k, "count": day_counts[k]} for k in sorted(day_counts.keys())]

    return {
        "days": days,
        "by_level": by_level,
        "total": len(alerts),
        "avg_resolution_hours": avg_hours,
        "top_site": {"name": top_site[0], "count": top_site[1]} if top_site else None,
        "trend": trend,
    }


def ingeniero_snapshot(db: Session) -> dict[str, Any]:
    runs = (
        db.query(EtlRun)
        .order_by(EtlRun.started_at.desc())
        .limit(10)
        .all()
    )
    models = (
        db.query(ModelRegistry)
        .order_by(ModelRegistry.trained_at.desc())
        .limit(10)
        .all()
    )
    jobs = (
        db.query(TrainingJob)
        .order_by(TrainingJob.started_at.desc())
        .limit(5)
        .all()
    )
    gas_dist = (
        db.query(Sensor.gas_type, func.count(Sensor.id))
        .group_by(Sensor.gas_type)
        .all()
    )
    return {
        "etl_runs": [
            {
                "id": r.id,
                "status": r.status,
                "started_at": format_datetime_short(r.started_at),
                "finished_at": format_datetime_short(r.finished_at),
                "rows_ingested": r.rows_ingested,
                "rows_rejected": r.rows_rejected,
            }
            for r in runs
        ],
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "version": m.version,
                "algorithm": m.algorithm,
                "status": m.status,
                "family": (m.params or {}).get("family"),
                "task": (m.params or {}).get("task"),
                "metrics": m.metrics or {},
                "trained_at": format_datetime_short(m.trained_at),
            }
            for m in models
        ],
        "jobs": [
            {
                "id": j.id,
                "status": j.status,
                "started_at": format_datetime_short(j.started_at),
                "finished_at": format_datetime_short(j.finished_at),
            }
            for j in jobs
        ],
        "gas_distribution": [
            {"gas_type": display_gas(g), "count": c} for g, c in gas_dist
        ],
    }


def recent_readings(db: Session, sensor_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        db.query(GasReading)
        .filter(GasReading.sensor_id == sensor_id)
        .order_by(GasReading.tiempo_inicio.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "leyendo": format_reading_value(r.leyendo),
            "unidad": r.unidad,
            "stel_max": r.stel_max,
            "twa_max": r.twa_max,
            "alarma": r.alarma,
            "tiempo_inicio": format_datetime_short(r.tiempo_inicio),
        }
        for r in rows
    ]


def recent_forecasts_for_sensor(
    db: Session, sensor_id: int, *, limit: int = 20
) -> list[dict[str, Any]]:
    from app.modules.forecasting.service import recent_for_sensor as _recent

    return _recent(db, sensor_id, limit=limit)


def notifications_for_alert(db: Session, alert_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(AlertNotification)
        .filter(AlertNotification.alert_id == alert_id)
        .order_by(AlertNotification.sent_at.desc().nullslast())
        .all()
    )
    return [
        {
            "id": n.id,
            "stakeholder_id": n.stakeholder_id,
            "channel": n.channel,
            "status": n.status,
            "error": n.error,
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
        }
        for n in rows
    ]
