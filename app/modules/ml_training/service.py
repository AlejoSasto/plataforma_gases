"""Servicio de entrenamiento, promote y modelo activo (zoo de forecasting, Plan 23 F5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.service import record_audit
from app.modules.ml_training import repository as repo
from app.modules.ml_training.models import ModelRegistry, TrainingJob
from app.modules.sensors_ingestion.models import GasReading, Sensor
from app.shared.exceptions import NotFoundError, ValidationError
from ml_core.forecasting.adapters import ADAPTERS, make_forecaster
from ml_core.forecasting.base import ZOO_KEYS, assert_prediction_frame
from ml_core.forecasting.problem import ProblemSpec
from ml_core.validation.metrics import forecast_metrics

SAFE_DEFAULT_ALGOS = ("persistencia", "ets")


def _job_to_dict(job: TrainingJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "model_registry_id": job.model_registry_id,
        "status": job.status,
        "dataset_version": job.dataset_version,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "triggered_by": job.triggered_by,
        "params": job.params or {},
        "log": job.log,
    }


def _model_to_dict(row: ModelRegistry) -> dict[str, Any]:
    params = row.params or {}
    metrics = row.metrics or {}
    return {
        "id": row.id,
        "name": row.name,
        "version": row.version,
        "algorithm": row.algorithm,
        "params": params,
        "metrics": metrics,
        "mlflow_run_id": row.mlflow_run_id,
        "artifact_uri": row.artifact_uri,
        "status": row.status,
        "scope": row.scope,
        "trained_by": row.trained_by,
        "trained_at": row.trained_at.isoformat() if row.trained_at else None,
        "family": params.get("family"),
        "task": params.get("task") or "forecast",
        "meets_thesis": None,
    }


def model_catalog() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in ZOO_KEYS:
        cls = ADAPTERS[key]
        sample = cls()
        out.append(
            {
                "key": key,
                "name": getattr(sample, "name", key),
                "family": getattr(sample, "family", "baseline"),
                "backend": getattr(sample, "backend", "native"),
                "task": "forecast",
            }
        )
    return out


def _readings_frame(db: Session, *, max_rows: int = 5000) -> pd.DataFrame:
    rows = (
        db.query(GasReading, Sensor)
        .join(Sensor, Sensor.id == GasReading.sensor_id)
        .filter(GasReading.is_synthetic.is_(False))
        .order_by(GasReading.tiempo_inicio.asc())
        .limit(max_rows)
        .all()
    )
    if len(rows) < 24:
        raise ValidationError("Hacen falta al menos 24 lecturas reales para entrenar")
    records = [
        {
            "unique_id": f"{sensor.code}|{sensor.gas_type}",
            "ds": reading.tiempo_inicio,
            "y": float(reading.leyendo) if reading.leyendo is not None else np.nan,
        }
        for reading, sensor in rows
    ]
    frame = pd.DataFrame.from_records(records).dropna(subset=["y"])
    if frame.empty:
        raise ValidationError("No hay lecturas numéricas para entrenar")
    return frame.sort_values(["unique_id", "ds"]).reset_index(drop=True)


def _normalize_algorithms(algorithms: list[str] | str | None) -> list[str]:
    if algorithms is None:
        return list(SAFE_DEFAULT_ALGOS)
    if isinstance(algorithms, str):
        algorithms = [a.strip() for a in algorithms.split(",") if a.strip()]
    keys = [a.strip().lower() for a in algorithms if a and str(a).strip()]
    unknown = [k for k in keys if k not in ADAPTERS]
    if unknown:
        raise ValidationError(
            f"Algoritmos no válidos para el zoo de forecasting: {unknown}. "
            f"Usa: {', '.join(ZOO_KEYS)}"
        )
    if not keys:
        return list(SAFE_DEFAULT_ALGOS)
    return keys


def start_training(
    db: Session,
    *,
    triggered_by: int,
    dataset_version: str = "gas_readings",
    params: dict[str, Any] | None = None,
    scope: str = "global",
    task: str = "forecast",
    algorithms: list[str] | str | None = None,
    lookback_steps: int | None = None,
    horizon_minutes: float | None = None,
) -> dict[str, Any]:
    """Entrena adaptadores de `ml_core.forecasting` (ya no el zoo tabular)."""
    if task in {"classification", "regression", "both"}:
        raise ValidationError(
            "El Laboratorio solo entrena pronóstico probabilístico (task=forecast). "
            "El zoo de clasificación/regresión se retiró (Plan 23 F5)."
        )
    task = "forecast"
    params = dict(params or {})
    params["task"] = task
    keys = _normalize_algorithms(algorithms)
    params["algorithms"] = keys
    lookback = int(lookback_steps or 60)
    params["lookback_steps"] = lookback
    if horizon_minutes is not None:
        params["horizon_minutes"] = horizon_minutes

    job = repo.create_job(
        db,
        dataset_version=dataset_version,
        triggered_by=triggered_by,
        params=params,
    )
    job_id = job.id
    db.commit()

    try:
        frame = _readings_frame(db, max_rows=int(params.get("max_rows") or 5000))
        spec = ProblemSpec(lookback=lookback, horizons=(6, 12, 18), grid_step_minutes=6)
        split = max(16, int(len(frame) * 0.7))
        train = frame.iloc[:split]
        val = frame.iloc[split:]
        if val.empty:
            val = train.tail(8)
            train = train.iloc[:-8]

        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        created_ids: list[int] = []
        results_log: list[dict[str, Any]] = []
        best_id: int | None = None
        best_mase = float("inf")
        art_root = Path("storage/models") / version
        art_root.mkdir(parents=True, exist_ok=True)

        for key in keys:
            model = make_forecaster(key)
            model.fit(train, spec)
            ctx = train.groupby("unique_id", group_keys=False).tail(max(spec.lookback, 2))
            pred = model.predict_quantiles(ctx, spec)
            assert_prediction_frame(pred)
            # Métricas groseras: comparar q50 del primer horizonte con último y de validación
            h0 = int(spec.horizons[0])
            sub = pred[pred["horizon_min"] == h0]
            y_true = val.groupby("unique_id")["y"].last().reindex(sub["unique_id"]).to_numpy(dtype=float)
            q50 = sub["q50"].to_numpy(dtype=float)
            q10 = sub["q10"].to_numpy(dtype=float)
            q90 = sub["q90"].to_numpy(dtype=float)
            persist = (
                train.groupby("unique_id")["y"].last().reindex(sub["unique_id"]).to_numpy(dtype=float)
            )
            mask = np.isfinite(y_true) & np.isfinite(q50) & np.isfinite(persist)
            metrics: dict[str, Any] = {"n": int(mask.sum()), "family": getattr(model, "family", None)}
            if mask.any():
                metrics.update(
                    forecast_metrics(
                        y_true[mask],
                        q10[mask],
                        q50[mask],
                        q90[mask],
                        y_persist=persist[mask],
                    )
                )
            path = art_root / key
            path.mkdir(parents=True, exist_ok=True)
            model.save(path)
            entry = repo.create_registry_entry(
                db,
                name=f"{key}-{version}",
                version=version,
                algorithm=key,
                params={
                    "family": getattr(model, "family", None),
                    "task": "forecast",
                    "backend": getattr(model, "backend", None),
                    "lookback": lookback,
                    "horizons": list(spec.horizons),
                    "library": getattr(model, "backend", "native"),
                },
                metrics=metrics,
                mlflow_run_id=None,
                artifact_uri=str(path),
                trained_by=triggered_by,
                status="staging",
                scope=scope,
            )
            created_ids.append(entry.id)
            results_log.append({"algorithm": key, "metrics": metrics, "id": entry.id})
            mase = float(metrics.get("mase") or 999)
            if mase < best_mase:
                best_mase = mase
                best_id = entry.id

        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).one()
        repo.finish_job(
            db,
            job,
            status="success",
            model_registry_id=best_id,
            log=json.dumps(
                {
                    "results": results_log,
                    "best_model_id": best_id,
                    "zoo": "forecasting",
                    "task": task,
                },
                default=str,
            ),
        )
        record_audit(
            db,
            action="ml.train",
            user_id=triggered_by,
            resource_type="training_job",
            resource_id=job.id,
            metadata={"best_model_id": best_id, "model_ids": created_ids, "zoo": "forecasting"},
        )
        db.commit()
        db.refresh(job)
        return {
            "job": _job_to_dict(job),
            "models": [_model_to_dict(repo.get_model(db, mid)) for mid in created_ids],
            "best_model_id": best_id,
        }
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).one()
        repo.finish_job(db, job, status="failed", log=str(exc))
        db.commit()
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"Entrenamiento falló: {exc}") from exc


def list_jobs(db: Session, *, page: int, page_size: int) -> dict[str, Any]:
    offset = (page - 1) * page_size
    items, total = repo.list_jobs(db, offset=offset, limit=page_size)
    return {
        "items": [_job_to_dict(j) for j in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_models(db: Session) -> list[dict[str, Any]]:
    return [_model_to_dict(m) for m in repo.list_models(db)]


def benchmark_for_assistant(
    db: Session,
    *,
    run_id: int | None,
    gas: str,
    horizonte: int | None,
) -> dict[str, Any]:
    """Resumen de una corrida. Sin rutas ni identificadores de archivos."""
    from app.modules.forecasting.models import BenchmarkRun
    from app.shared.gas_catalog import canonicalize_gas_type, display_gas

    query = db.query(BenchmarkRun).order_by(BenchmarkRun.created_at.desc())
    if run_id is not None:
        query = db.query(BenchmarkRun).filter(BenchmarkRun.id == run_id)
    row = query.first()
    if row is None:
        return {"error": "Todavía no hay una corrida de resultados para consultar."}
    report = row.selection_report or ""
    if len(report) > 1200:
        report = report[:1200]
    return {
        "corrida": row.id,
        "gas": display_gas(canonicalize_gas_type(gas)),
        "horizonte_min": horizonte,
        "metodo_elegido": row.promoted_algorithm,
        "por_que": report or "La corrida no dejó una explicación escrita.",
        "creada": row.created_at.isoformat() if row.created_at else None,
    }


def compare_models(db: Session) -> list[dict[str, Any]]:
    return [_model_to_dict(m) for m in repo.list_models(db)]


def propose_production(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    from ml_core.experiments.select import select_production_model

    result = select_production_model(evaluations)
    return {
        "winner": result.winner,
        "eligible": result.eligible,
        "score": result.score,
        "reason": result.reason,
        "ranking": result.ranking,
    }


def promote_model(
    db: Session,
    model_id: int,
    *,
    actor_id: int,
    scope: str | None = None,
) -> dict[str, Any]:
    model = repo.get_model(db, model_id)
    if model is None:
        raise NotFoundError("Modelo no encontrado")
    target_scope = scope or model.scope or "global"
    task = (model.params or {}).get("task") or "forecast"
    repo.archive_production(db, scope=target_scope, task=task)
    model.status = "production"
    model.scope = target_scope
    db.add(model)
    record_audit(
        db,
        action="ml.promote",
        user_id=actor_id,
        resource_type="model_registry",
        resource_id=model.id,
        metadata={"scope": target_scope, "algorithm": model.algorithm, "task": task},
    )
    db.commit()
    db.refresh(model)
    return _model_to_dict(model)


def get_active_model(db: Session, scope: str = "global", task: str = "forecast") -> Any:
    """Devuelve la fila production (artefacto en disco del zoo de forecasting)."""
    row = repo.get_production_model(db, scope=scope, task=task)
    if row is None:
        row = repo.get_production_model(db, scope=scope, task=None)
    if row is None:
        raise NotFoundError(f"No hay modelo production para scope={scope}")
    if not row.artifact_uri:
        raise ValidationError("El modelo production no tiene artifact_uri")
    key = row.algorithm
    if key not in ADAPTERS:
        raise ValidationError(f"Algoritmo production no está en el zoo vigente: {key}")
    return make_forecaster(key).load(Path(row.artifact_uri))
