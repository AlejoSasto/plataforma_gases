"""E5: persistencia idempotente en tablas actuales (Plan 16 añadirá UNIQUE)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.ingestion.pipeline.hashing import already_loaded, source_record
from app.modules.ingestion.pipeline.types import StageResult
from app.modules.sensors_ingestion import repository as repo
from app.modules.sensors_ingestion.models import EtlRun, GasReading
from app.shared.gas_catalog import normalize_site_name


def list_loaded_hashes(db: Session) -> set[str]:
    hashes: set[str] = set()
    for run in db.query(EtlRun).all():
        for item in run.source_files or []:
            if isinstance(item, dict) and item.get("sha256"):
                hashes.add(str(item["sha256"]))
    return hashes


def e5_load(
    db: Session,
    df: pd.DataFrame,
    *,
    source_path: Path | str,
    skip_if_loaded: bool = True,
    triggered_by_user_id: int | None = None,
) -> StageResult:
    rec = source_record(source_path)
    rows_in = int(len(df))
    if skip_if_loaded and rec["sha256"] in list_loaded_hashes(db):
        return StageResult(
            name="E5",
            dataframe=df,
            rows_in=rows_in,
            rows_out=0,
            details={"skipped": True, "reason": "sha256_already_loaded", "source": rec},
        )

    run = repo.create_etl_run(
        db,
        triggered_by_user_id=triggered_by_user_id,
        source_files=[rec],
    )
    inserted = 0
    omitted = 0
    cache_site: dict[str, Any] = {}
    cache_sensor: dict[tuple[str, str], Any] = {}
    batch: list[dict[str, Any]] = []

    usable = df
    if "quality_status" in df.columns:
        usable = df[df["quality_status"] != "excluida"].copy()

    seen_keys: set[tuple[int, object]] = set()
    existing = {
        (r.sensor_id, r.tiempo_inicio)
        for r in db.query(GasReading.sensor_id, GasReading.tiempo_inicio).all()
    }

    for _, row in usable.iterrows():
        site_name = normalize_site_name(row.get("site_name"))
        if site_name not in cache_site:
            cache_site[site_name] = repo.get_or_create_site(db, site_name)
        site = cache_site[site_name]
        sensor_code = str(row.get("sensor_code"))
        gas = str(row.get("gas"))
        key_s = (sensor_code, gas)
        if key_s not in cache_sensor:
            cache_sensor[key_s] = repo.get_or_create_sensor(
                db,
                site=site,
                code=sensor_code,
                gas_type=gas,
                unit=str(row.get("unit_canonical") or row.get("Unidad") or "") or None,
            )
        sensor = cache_sensor[key_s]
        t0 = pd.to_datetime(row["Tiempo de Inicio"], utc=True).to_pydatetime()
        key = (sensor.id, t0)
        if key in existing or key in seen_keys:
            omitted += 1
            continue
        seen_keys.add(key)
        val = float(row.get("value_canonical") if pd.notna(row.get("value_canonical")) else row["Leyendo"])
        batch.append(
            {
                "sensor_id": sensor.id,
                "leyendo": val,
                "unidad": str(row.get("unit_canonical") or row.get("Unidad") or "") or None,
                "stel_max": None,
                "twa_max": None,
                "alarma": str(row["Alarma"]) if "Alarma" in row and pd.notna(row.get("Alarma")) else None,
                "temperatura": float(row["Temperatura"])
                if "Temperatura" in row and pd.notna(row.get("Temperatura"))
                else None,
                "tiempo_inicio": t0,
                "tiempo_fin": pd.to_datetime(row["Tiempo de finalización"], utc=True).to_pydatetime()
                if "Tiempo de finalización" in row and pd.notna(row.get("Tiempo de finalización"))
                else None,
                "is_synthetic": False,
                "source_file": rec["name"],
                "etl_run_id": run.id,
            }
        )

    inserted = repo.bulk_insert_readings(db, batch)
    repo.update_etl_run(
        db,
        run,
        status="success",
        rows_ingested=inserted,
        rows_rejected=omitted,
        source_files=[rec],
        log={"e5": {"inserted": inserted, "omitted_duplicates": omitted, "source": rec}},
    )
    db.commit()
    return StageResult(
        name="E5",
        dataframe=df,
        rows_in=rows_in,
        rows_out=inserted,
        rows_rejected=omitted,
        details={"inserted": inserted, "omitted_duplicates": omitted, "etl_run_id": run.id, "source": rec},
    )
