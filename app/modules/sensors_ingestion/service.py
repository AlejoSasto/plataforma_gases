"""Servicio de orquestación ETL."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.audit.service import record_audit
from app.modules.sensors_ingestion import repository as repo
from app.modules.sensors_ingestion.models import EtlRun
from app.shared.gas_catalog import (
    canonicalize_gas_type,
    normalize_sensor_code,
    normalize_site_name,
)
from ml_core.columns import EXPECTED_COLUMNS
from ml_core.data_io import CleanResult, load_and_clean, load_and_clean_csv


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _to_dt(value: Any) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    dt = ts.to_pydatetime()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _dataframe_to_readings(
    db: Session,
    df: pd.DataFrame,
    *,
    etl_run_id: int,
    default_synthetic: bool = False,
) -> list[dict[str, Any]]:
    if df.empty:
        return []

    cache_site: dict[str, Any] = {}
    cache_sensor: dict[tuple[str, str], Any] = {}
    readings: list[dict[str, Any]] = []

    has_synth_col = "is_synthetic" in df.columns
    records = df.to_dict(orient="records")
    for row in records:
        site_name = normalize_site_name(_to_str(row.get("Sitio")))
        if site_name not in cache_site:
            cache_site[site_name] = repo.get_or_create_site(db, site_name)
        site = cache_site[site_name]

        sensor_code = normalize_sensor_code(_to_str(row.get("Sensor")))
        gas_type = canonicalize_gas_type(
            _to_str(row.get("Descripción")) or _to_str(row.get("Gas"))
        )
        unit = _to_str(row.get("Unidad"))
        sensor_key = (sensor_code, gas_type)
        if sensor_key not in cache_sensor:
            cache_sensor[sensor_key] = repo.get_or_create_sensor(
                db, site=site, code=sensor_code, gas_type=gas_type, unit=unit
            )
        sensor = cache_sensor[sensor_key]

        is_synth = default_synthetic
        if has_synth_col:
            val = row.get("is_synthetic")
            if isinstance(val, (bool, int)):
                is_synth = bool(val)

        tiempo_inicio = _to_dt(row.get("Tiempo de Inicio"))
        leyendo = _to_float(row.get("Leyendo"))
        if tiempo_inicio is None or leyendo is None:
            continue

        readings.append(
            {
                "sensor_id": sensor.id,
                "leyendo": leyendo,
                "unidad": unit,
                "stel_max": _to_float(row.get("STEL Máx")),
                "twa_max": _to_float(row.get("TWA máximo")),
                "alarma": _to_str(row.get("Alarma")),
                "temperatura": _to_float(row.get("Temperatura")),
                "tiempo_inicio": tiempo_inicio,
                "tiempo_fin": _to_dt(row.get("Tiempo de finalización")),
                "is_synthetic": is_synth,
                "source_file": _to_str(row.get("_source_file")),
                "etl_run_id": etl_run_id,
            }
        )
    return readings


def _build_log(clean: CleanResult, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    df = clean.dataframe
    date_min = date_max = None
    if not df.empty and "Tiempo de Inicio" in df.columns:
        valid = df["Tiempo de Inicio"].dropna()
        if not valid.empty:
            date_min = str(valid.min())
            date_max = str(valid.max())

    log: dict[str, Any] = {
        "transforms": clean.transforms,
        "expected_columns": EXPECTED_COLUMNS,
        "source_files": clean.source_files,
        "warnings": clean.warnings,
        "rejected_sample": clean.rejected[:50],
        "rejected_total": len(clean.rejected),
        "date_range": {"min": date_min, "max": date_max},
        "rows_clean": int(len(df)),
    }
    if extra:
        log.update(extra)
    return log


def _persist_clean_result(
    db: Session,
    clean: CleanResult,
    *,
    triggered_by_user_id: int | None,
    is_synthetic_default: bool = False,
    audit: bool = False,
    extra_log: dict[str, Any] | None = None,
) -> EtlRun:
    run = repo.create_etl_run(
        db,
        triggered_by_user_id=triggered_by_user_id,
        source_files=clean.source_files,
    )
    try:
        readings = _dataframe_to_readings(
            db,
            clean.dataframe,
            etl_run_id=run.id,
            default_synthetic=is_synthetic_default,
        )
        ingested = repo.bulk_insert_readings(db, readings)
        log = _build_log(clean, extra_log)
        status = "success" if ingested > 0 or not clean.warnings else "success"
        if ingested == 0 and clean.dataframe.empty:
            status = "failed" if clean.warnings else "success"
        repo.update_etl_run(
            db,
            run,
            status=status,
            rows_ingested=ingested,
            rows_rejected=len(clean.rejected),
            source_files=clean.source_files,
            log=log,
        )
        if audit and triggered_by_user_id is not None:
            record_audit(
                db,
                action="ingestion.upload",
                user_id=triggered_by_user_id,
                resource_type="etl_run",
                resource_id=run.id,
                metadata={
                    "rows_ingested": ingested,
                    "rows_rejected": len(clean.rejected),
                    "source_files": clean.source_files,
                },
            )
        db.commit()
        db.refresh(run)
        if status == "success" and ingested > 0:
            log = dict(run.log or {})
            log["forecasts"] = {"skipped": 1, "reason": "plan_17"}
            run.log = log
            db.add(run)
            db.commit()
            db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        failed = repo.create_etl_run(
            db,
            triggered_by_user_id=triggered_by_user_id,
            source_files=clean.source_files,
        )
        repo.update_etl_run(
            db,
            failed,
            status="failed",
            rows_ingested=0,
            rows_rejected=len(clean.rejected),
            source_files=clean.source_files,
            log={**_build_log(clean, extra_log), "error": str(exc)},
        )
        db.commit()
        db.refresh(failed)
        return failed


def ingest_excel_paths(
    db: Session,
    paths: list[Path],
    *,
    triggered_by_user_id: int | None = None,
    audit: bool = False,
) -> EtlRun:
    clean = load_and_clean(paths)
    return _persist_clean_result(
        db,
        clean,
        triggered_by_user_id=triggered_by_user_id,
        is_synthetic_default=False,
        audit=audit,
    )


def ingest_csv_paths(
    db: Session,
    paths: list[Path],
    *,
    is_synthetic: bool = False,
    triggered_by_user_id: int | None = None,
    mark_against_real: Path | None = None,
    manifest_path: Path | None = None,
) -> EtlRun:
    if is_synthetic or mark_against_real is not None or manifest_path is not None:
        raise ValueError("Carga sintética / 24m retirada (Plan 15 F1). Solo datos reales.")
    clean = load_and_clean_csv(paths)
    extra: dict[str, Any] = {"is_synthetic_default": False}
    return _persist_clean_result(
        db,
        clean,
        triggered_by_user_id=triggered_by_user_id,
        is_synthetic_default=False,
        audit=False,
        extra_log=extra,
    )


def etl_run_to_dict(run: EtlRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status,
        "rows_ingested": run.rows_ingested,
        "rows_rejected": run.rows_rejected,
        "source_files": run.source_files or [],
        "log": run.log or {},
        "triggered_by_user_id": run.triggered_by_user_id,
    }
