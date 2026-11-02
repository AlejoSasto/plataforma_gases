"""Servicio de entrenamiento, promote y modelo activo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import mlflow
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit.service import record_audit
from app.modules.ml_training import repository as repo
from app.modules.ml_training.models import ModelRegistry, TrainingJob
from app.shared.exceptions import NotFoundError, ValidationError
from ml_core.models.registry import catalog_public
from ml_core.models.train_model import best_result, result_to_dict, train


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
    gates = metrics.get("gates") or {}
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
        "task": params.get("task"),
        "meets_thesis": gates.get("meets_thesis"),
    }


def start_training(
    db: Session,
    *,
    triggered_by: int,
    dataset_version: str = "gas_readings",
    params: dict[str, Any] | None = None,
    scope: str = "global",
    task: str = "classification",
    algorithms: list[str] | str | None = None,
    lookback_steps: int | None = None,
    horizon_minutes: float | None = None,
) -> dict[str, Any]:
    params = dict(params or {})
    params["task"] = task
    if algorithms is not None:
        params["algorithms"] = algorithms
    if lookback_steps is not None:
        params["lookback_steps"] = lookback_steps
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
        results = train(
            db,
            dataset_version=dataset_version,
            params=params,
            triggered_by_user_id=triggered_by,
        )
        best = best_result(results)
        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        created_ids: list[int] = []
        best_id: int | None = None

        job = db.query(TrainingJob).filter(TrainingJob.id == job_id).one()
        for result in results:
            entry = repo.create_registry_entry(
                db,
                name=f"{result.algorithm}-{version}",
                version=version,
                algorithm=result.algorithm,
                params=result.params,
                metrics=result.metrics,
                mlflow_run_id=result.mlflow_run_id,
                artifact_uri=result.artifact_uri,
                trained_by=triggered_by,
                status="staging",
                scope=scope,
            )
            created_ids.append(entry.id)
            if result.algorithm == best.algorithm:
                best_id = entry.id

        repo.finish_job(
            db,
            job,
            status="success",
            model_registry_id=best_id,
            log=json.dumps(
                {
                    "results": [result_to_dict(r) for r in results],
                    "best_algorithm": best.algorithm,
                    "registry_ids": created_ids,
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
            metadata={"best_algorithm": best.algorithm, "model_ids": created_ids},
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


def compare_models(db: Session) -> list[dict[str, Any]]:
    return [_model_to_dict(m) for m in repo.list_models(db)]


def propose_production(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    """Propone ganador. La promoción sigue siendo explícita (`models.promote`)."""
    from ml_core.experiments.select import select_production_model

    result = select_production_model(evaluations)
    return {
        "winner": result.winner,
        "eligible": result.eligible,
        "score": result.score,
        "reason": result.reason,
        "ranking": result.ranking,
    }


def model_catalog() -> list[dict[str, Any]]:
    return catalog_public()


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
    task = (model.params or {}).get("task") or "classification"
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


def get_active_model(db: Session, scope: str = "global", task: str = "classification") -> Any:
    """Carga el modelo production (sklearn/xgb via mlflow pyfunc)."""
    row = repo.get_production_model(db, scope=scope, task=task)
    if row is None:
        row = repo.get_production_model(db, scope=scope, task=None)
    if row is None:
        raise NotFoundError(f"No hay modelo production para scope={scope}")
    if not row.artifact_uri:
        raise ValidationError("El modelo production no tiene artifact_uri")
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    return mlflow.pyfunc.load_model(row.artifact_uri)
