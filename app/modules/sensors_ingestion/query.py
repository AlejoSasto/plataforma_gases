"""Lecturas, episodios y cobertura para las herramientas del asistente.

Las herramientas no consultan la base: llaman estas funciones del módulo de sensores.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.catalog.models import AppSetting, GasType, NormativeThreshold
from app.modules.sensors_ingestion.models import (
    DataQualityIssue,
    GasReading,
    Instrument,
    ReadingGrid,
    Sensor,
    ThresholdEvent,
)
from app.modules.users.models import User
from app.shared.gas_catalog import canonicalize_gas_type, display_gas

BOGOTA = ZoneInfo("America/Bogota")
MAX_ROWS = 200
MAX_DAYS = 400


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def data_bounds(db: Session, sensor_ids: list[int]) -> tuple[datetime | None, datetime | None]:
    if not sensor_ids:
        return None, None
    row = (
        db.query(func.min(GasReading.tiempo_inicio), func.max(GasReading.tiempo_inicio))
        .filter(GasReading.sensor_id.in_(sensor_ids))
        .one()
    )
    start, end = row
    if start is None or end is None:
        return None, None
    return _as_utc(start), _as_utc(end)


def clamp_period(
    start: datetime | None,
    end: datetime | None,
    bounds: tuple[datetime | None, datetime | None],
) -> tuple[datetime, datetime, bool] | dict[str, str]:
    data_min, data_max = bounds
    if data_min is None or data_max is None:
        return {"error": "No hay lecturas en tu alcance."}
    clamped = False
    if start is None or end is None:
        start = start or data_min
        end = end or data_max
        clamped = True
    start = _as_utc(start)
    end = _as_utc(end)
    if end < start:
        return {"error": "La fecha final tiene que ser posterior a la inicial."}
    if start < data_min:
        start = data_min
        clamped = True
    if end > data_max:
        end = data_max
        clamped = True
    if start > end:
        start, end = data_min, data_max
        clamped = True
    if (end - start).days > MAX_DAYS:
        start = end - timedelta(days=MAX_DAYS)
        if start < data_min:
            start = data_min
        clamped = True
    return start, end, clamped


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat()


def _bucket(moment: datetime, aggregation: str) -> str:
    local = _as_utc(moment).astimezone(BOGOTA)
    if aggregation == "hora":
        return local.strftime("%Y-%m-%d %H:00")
    if aggregation == "dia":
        return local.strftime("%Y-%m-%d")
    floored = local.replace(minute=(local.minute // 6) * 6, second=0, microsecond=0)
    return floored.strftime("%Y-%m-%d %H:%M")


def _metric_value(reading: GasReading, grid: ReadingGrid | None, metric: str) -> float | None:
    if metric == "twa_8h":
        if grid is not None and grid.twa_8h is not None:
            return float(grid.twa_8h)
        if reading.twa_max is not None:
            return float(reading.twa_max)
        return None
    if metric == "stel_15min":
        if grid is not None and grid.stel_15min is not None:
            return float(grid.stel_15min)
        if reading.stel_max is not None:
            return float(reading.stel_max)
        return None
    if reading.value_canonical is not None:
        return float(reading.value_canonical)
    return float(reading.leyendo)


def _sensors_for_gas(db: Session, sensor_ids: list[int], gas: str) -> list[Sensor]:
    code = canonicalize_gas_type(gas)
    rows = db.query(Sensor).filter(Sensor.id.in_(sensor_ids or [-1])).all()
    return [row for row in rows if canonicalize_gas_type(row.gas_type) == code]


def series_summary(
    db: Session,
    *,
    sensor_ids: list[int],
    gas: str,
    start: datetime,
    end: datetime,
    aggregation: str,
    metric: str,
) -> dict[str, Any]:
    sensors = _sensors_for_gas(db, sensor_ids, gas)
    if not sensors:
        return {"error": "No hay un equipo con ese gas en tu alcance."}
    ids = [row.id for row in sensors]
    readings = (
        db.query(GasReading)
        .filter(
            GasReading.sensor_id.in_(ids),
            GasReading.tiempo_inicio >= start,
            GasReading.tiempo_inicio <= end,
        )
        .order_by(GasReading.tiempo_inicio.asc())
        .all()
    )
    grid_rows = (
        db.query(ReadingGrid)
        .filter(
            ReadingGrid.sensor_id.in_(ids),
            ReadingGrid.ts >= start,
            ReadingGrid.ts <= end,
        )
        .all()
    )
    grid_index = {(row.sensor_id, _as_utc(row.ts).replace(microsecond=0)): row for row in grid_rows}
    values: list[float] = []
    buckets: dict[str, list[float]] = {}
    for reading in readings:
        key = (reading.sensor_id, _as_utc(reading.tiempo_inicio).replace(microsecond=0))
        value = _metric_value(reading, grid_index.get(key), metric)
        if value is None:
            continue
        values.append(value)
        buckets.setdefault(_bucket(reading.tiempo_inicio, aggregation), []).append(value)
    points = [
        {"t": label, "v": round(sum(nums) / len(nums), 4)}
        for label, nums in list(buckets.items())[:MAX_ROWS]
    ]
    if not values:
        return {
            "n": 0,
            "min": None,
            "max": None,
            "avg": None,
            "points": [],
            "note": "No hay lecturas en ese periodo.",
        }
    return {
        "n": len(values),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "avg": round(sum(values) / len(values), 4),
        "points": points,
        "gas": canonicalize_gas_type(gas),
        "gas_label": display_gas(gas),
        "metric": metric,
        "aggregation": aggregation,
    }


def _group_key(moment: datetime, sensor: Sensor, mode: str, instrument_name: str) -> str:
    local = _as_utc(moment).astimezone(BOGOTA)
    if mode == "semana":
        year, week, _ = local.isocalendar()
        return f"{year}-W{week:02d}"
    if mode == "mes":
        return local.strftime("%Y-%m")
    if mode == "equipo":
        return instrument_name or sensor.code
    if mode == "turno":
        hour = local.hour
        if 6 <= hour < 14:
            return "Turno mañana"
        if 14 <= hour < 22:
            return "Turno tarde"
        return "Turno noche"
    return local.strftime("%Y-%m-%d")


def _exceeds(value: float, row: NormativeThreshold) -> bool:
    limit = float(row.value)
    if row.direction == "below":
        return value < limit
    return value > limit


def grouped_stats(
    db: Session,
    *,
    sensor_ids: list[int],
    gas: str,
    start: datetime,
    end: datetime,
    agrupar_por: str,
) -> dict[str, Any]:
    sensors = _sensors_for_gas(db, sensor_ids, gas)
    if not sensors:
        return {"error": "No hay un equipo con ese gas en tu alcance."}
    code = canonicalize_gas_type(gas)
    by_id = {row.id: row for row in sensors}
    names: dict[int, str] = {}
    instrument_ids = {row.instrument_id for row in sensors if row.instrument_id}
    instruments = (
        db.query(Instrument).filter(Instrument.id.in_(instrument_ids or [-1])).all()
        if instrument_ids
        else []
    )
    serial = {row.id: row.serial for row in instruments}
    for sensor in sensors:
        names[sensor.id] = serial.get(sensor.instrument_id) or sensor.code
    limits = (
        db.query(NormativeThreshold)
        .filter(NormativeThreshold.gas_code == code)
        .all()
    )
    readings = (
        db.query(GasReading)
        .filter(
            GasReading.sensor_id.in_(list(by_id)),
            GasReading.tiempo_inicio >= start,
            GasReading.tiempo_inicio <= end,
        )
        .order_by(GasReading.tiempo_inicio.asc())
        .all()
    )
    groups: dict[str, dict[str, Any]] = {}
    for reading in readings:
        sensor = by_id[reading.sensor_id]
        value = float(reading.value_canonical if reading.value_canonical is not None else reading.leyendo)
        key = _group_key(reading.tiempo_inicio, sensor, agrupar_por, names.get(sensor.id, sensor.code))
        bucket = groups.setdefault(
            key,
            {"grupo": key, "n": 0, "min": value, "max": value, "sum": 0.0, "superaciones": {}},
        )
        bucket["n"] += 1
        bucket["min"] = min(bucket["min"], value)
        bucket["max"] = max(bucket["max"], value)
        bucket["sum"] += value
        for limit in limits:
            if _exceeds(value, limit):
                label = limit.level
                bucket["superaciones"][label] = bucket["superaciones"].get(label, 0) + 1
    rows = []
    for bucket in list(groups.values())[:MAX_ROWS]:
        rows.append(
            {
                "grupo": bucket["grupo"],
                "n": bucket["n"],
                "min": round(bucket["min"], 4),
                "max": round(bucket["max"], 4),
                "avg": round(bucket["sum"] / bucket["n"], 4) if bucket["n"] else None,
                "superaciones": bucket["superaciones"],
            }
        )
    return {"grupos": rows, "n_grupos": len(rows), "gas": code, "gas_label": display_gas(gas)}


def episodes(
    db: Session,
    *,
    sensor_ids: list[int],
    gas: str,
    start: datetime,
    end: datetime,
    nivel: str | None,
) -> dict[str, Any]:
    from app.modules.alerts.models import Alert

    sensors = _sensors_for_gas(db, sensor_ids, gas)
    if not sensors:
        return {"error": "No hay un equipo con ese gas en tu alcance."}
    code = canonicalize_gas_type(gas)
    ids = [row.id for row in sensors]
    query = db.query(ThresholdEvent).filter(
        ThresholdEvent.sensor_id.in_(ids),
        ThresholdEvent.gas_code == code,
        ThresholdEvent.started_at <= end,
        func.coalesce(ThresholdEvent.ended_at, ThresholdEvent.started_at) >= start,
    )
    if nivel:
        query = query.filter(ThresholdEvent.level == nivel)
    events = query.order_by(ThresholdEvent.started_at.asc()).limit(MAX_ROWS).all()
    names = {row.id: row.code for row in sensors}
    rows = []
    for event in events:
        prior = (
            db.query(Alert.id)
            .filter(
                Alert.sensor_id == event.sensor_id,
                Alert.created_at <= event.started_at,
                Alert.created_at >= event.started_at - timedelta(hours=12),
            )
            .first()
        )
        rows.append(
            {
                "inicio": _iso(event.started_at),
                "fin": _iso(event.ended_at),
                "pico": float(event.peak_value) if event.peak_value is not None else None,
                "equipo": names.get(event.sensor_id),
                "nivel": event.level,
                "aviso_previo": prior is not None,
            }
        )
    return {"episodios": rows, "n": len(rows), "gas_label": display_gas(gas)}


def coverage(db: Session, user: User, sensor_ids: list[int]) -> dict[str, Any]:
    start, end = data_bounds(db, sensor_ids)
    sensors = db.query(Sensor).filter(Sensor.id.in_(sensor_ids or [-1])).all()
    gases = sorted({canonicalize_gas_type(row.gas_type) for row in sensors if row.gas_type})
    instrument_ids = {row.instrument_id for row in sensors if row.instrument_id}
    quality = (
        db.query(func.count(DataQualityIssue.id))
        .filter(DataQualityIssue.sensor_id.in_(sensor_ids or [-1]))
        .scalar()
    )
    g1 = db.get(AppSetting, "g1_params")
    gases_catalog = [row.code for row in db.query(GasType).filter(GasType.is_active.is_(True)).all()]
    return {
        "desde": _iso(start),
        "hasta": _iso(end),
        "equipos": len(instrument_ids) or len({row.code for row in sensors}),
        "sensores": len(sensors),
        "gases": gases,
        "gases_catalogo": gases_catalog,
        "avisos_calidad": int(quality or 0),
        "parametros_g1": g1.value if g1 is not None else None,
        "usuario": user.id,
    }


def known_gases(db: Session) -> set[str]:
    rows = db.query(GasType.code).filter(GasType.is_active.is_(True)).all()
    return {row[0] for row in rows} or {"CH4", "CO", "H2S", "CO2", "O2", "NO2"}
