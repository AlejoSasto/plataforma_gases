"""Repositorio de ingesta de sensores."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy.orm import Session

from app.modules.sensors_ingestion.models import EtlRun, GasReading, Sensor, Site

BATCH_SIZE = 5000


def get_or_create_site(db: Session, name: str, description: str | None = None) -> Site:
    site_name = (name or "").strip() or "SIN_SITIO"
    site = db.query(Site).filter(Site.name == site_name).first()
    if site is None:
        site = Site(name=site_name, description=description)
        db.add(site)
        db.flush()
    return site


def get_or_create_sensor(
    db: Session,
    *,
    site: Site,
    code: str,
    gas_type: str,
    unit: str | None,
) -> Sensor:
    sensor_code = (code or "").strip() or "UNKNOWN_SENSOR"
    gas = (gas_type or "").strip() or "UNKNOWN"
    sensor = (
        db.query(Sensor)
        .filter(Sensor.code == sensor_code, Sensor.gas_type == gas)
        .first()
    )
    if sensor is None:
        sensor = Sensor(site_id=site.id, code=sensor_code, gas_type=gas, unit=unit)
        db.add(sensor)
        db.flush()
    elif unit and not sensor.unit:
        sensor.unit = unit
        db.add(sensor)
        db.flush()
    return sensor


def create_etl_run(
    db: Session,
    *,
    triggered_by_user_id: int | None = None,
    source_files: list[str] | None = None,
) -> EtlRun:
    run = EtlRun(
        status="running",
        rows_ingested=0,
        rows_rejected=0,
        source_files=source_files or [],
        log={},
        triggered_by_user_id=triggered_by_user_id,
    )
    db.add(run)
    db.flush()
    return run


def update_etl_run(
    db: Session,
    run: EtlRun,
    *,
    status: str,
    rows_ingested: int | None = None,
    rows_rejected: int | None = None,
    source_files: list[str] | None = None,
    log: dict[str, Any] | None = None,
) -> EtlRun:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    if rows_ingested is not None:
        run.rows_ingested = rows_ingested
    if rows_rejected is not None:
        run.rows_rejected = rows_rejected
    if source_files is not None:
        run.source_files = source_files
    if log is not None:
        run.log = log
    db.add(run)
    db.flush()
    return run


def bulk_insert_readings(db: Session, readings: Sequence[dict[str, Any]]) -> int:
    if not readings:
        return 0
    total = 0
    for i in range(0, len(readings), BATCH_SIZE):
        chunk = list(readings[i : i + BATCH_SIZE])
        db.bulk_insert_mappings(GasReading, chunk)
        db.flush()
        total += len(chunk)
    return total


def list_etl_runs(
    db: Session, *, offset: int, limit: int
) -> tuple[list[EtlRun], int]:
    total = db.query(EtlRun).count()
    items = (
        db.query(EtlRun)
        .order_by(EtlRun.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def get_etl_run(db: Session, run_id: int) -> Optional[EtlRun]:
    return db.query(EtlRun).filter(EtlRun.id == run_id).first()
