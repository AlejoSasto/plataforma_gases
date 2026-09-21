"""Servicios de datos para el dashboard (semáforo, series, KPIs)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.alerts import service as alerts_service
from app.modules.ml_training.models import ModelRegistry, TrainingJob
from app.modules.predictions.models import Prediction
from app.modules.sensors_ingestion.models import EtlRun, GasReading, Sensor, Site
from app.modules.stakeholders.models import AlertNotification
from app.modules.stakeholders.service import alert_ids_visible_to_user
from app.shared.exceptions import NotFoundError
from app.shared.formatting import format_datetime_short, format_reading_value

LEVEL_RANK = {"NORMAL": 0, "PRECAUCION": 1, "ALERTA": 2, "CRITICO": 3}


def list_sites(db: Session) -> list[dict[str, Any]]:
    sites = db.query(Site).order_by(Site.name.asc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "sensors_count": len(s.sensors or []),
        }
        for s in sites
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


def semaforo(db: Session, *, site_id: Optional[int] = None) -> list[dict[str, Any]]:
    q = db.query(Sensor, Site).join(Site, Sensor.site_id == Site.id)
    if site_id is not None:
        q = q.filter(Sensor.site_id == site_id)
    rows = q.order_by(Site.name.asc(), Sensor.code.asc()).all()
    result: list[dict[str, Any]] = []
    for sensor, site in rows:
        last_reading = (
            db.query(GasReading)
            .filter(GasReading.sensor_id == sensor.id)
            .order_by(GasReading.tiempo_inicio.desc())
            .first()
        )
        last_pred = None
        if last_reading is not None:
            last_pred = (
                db.query(Prediction)
                .filter(Prediction.gas_reading_id == last_reading.id)
                .order_by(Prediction.created_at.desc())
                .first()
            )
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
        elif last_pred is not None and last_pred.risk_level:
            risk = last_pred.risk_level
        result.append(
            {
                "sensor_id": sensor.id,
                "sensor_code": sensor.code,
                "gas_type": sensor.gas_type,
                "unit": sensor.unit,
                "site_id": site.id,
                "site_name": site.name,
                "risk_level": risk,
                "last_value": format_reading_value(last_reading.leyendo)
                if last_reading
                else None,
                "last_at": format_datetime_short(last_reading.tiempo_inicio)
                if last_reading
                else None,
                "probability": last_pred.probability if last_pred else None,
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
    sensor = get_sensor(db, sensor_id)
    site = db.query(Site).filter(Site.id == sensor.site_id).first()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    readings = (
        db.query(GasReading)
        .filter(GasReading.sensor_id == sensor_id, GasReading.tiempo_inicio >= since)
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
        "sensor_code": sensor.code,
        "gas_type": sensor.gas_type,
        "unit": sensor.unit,
        "site_id": sensor.site_id,
        "site_name": site.name if site else None,
        "hours": hours,
        "points": points,
        "stel_max": last.stel_max if last else None,
        "twa_max": last.twa_max if last else None,
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
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
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
                "metrics": m.metrics or {},
                "trained_at": m.trained_at.isoformat() if m.trained_at else None,
            }
            for m in models
        ],
        "jobs": [
            {
                "id": j.id,
                "status": j.status,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            }
            for j in jobs
        ],
        "gas_distribution": [{"gas_type": g or "UNKNOWN", "count": c} for g, c in gas_dist],
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


def recent_predictions_for_sensor(
    db: Session, sensor_id: int, *, limit: int = 20
) -> list[dict[str, Any]]:
    rows = (
        db.query(Prediction)
        .join(GasReading, Prediction.gas_reading_id == GasReading.id)
        .filter(GasReading.sensor_id == sensor_id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.id,
            "probability": format_reading_value(p.probability, decimals=3),
            "risk_level": p.risk_level,
            "predicted_label": p.predicted_label,
            "created_at": format_datetime_short(p.created_at),
            "model_registry_id": p.model_registry_id,
        }
        for p in rows
    ]


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
