"""Repositorio de entrenamiento ML."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.ml_training.models import ModelRegistry, TrainingJob


def create_job(
    db: Session,
    *,
    dataset_version: str,
    triggered_by: int | None,
    params: dict[str, Any] | None,
) -> TrainingJob:
    job = TrainingJob(
        status="running",
        dataset_version=dataset_version,
        triggered_by=triggered_by,
        params=params or {},
    )
    db.add(job)
    db.flush()
    return job


def finish_job(
    db: Session,
    job: TrainingJob,
    *,
    status: str,
    model_registry_id: int | None = None,
    log: str | None = None,
) -> TrainingJob:
    job.status = status
    job.finished_at = datetime.now(timezone.utc)
    if model_registry_id is not None:
        job.model_registry_id = model_registry_id
    if log is not None:
        job.log = log
    db.add(job)
    db.flush()
    return job


def create_registry_entry(
    db: Session,
    *,
    name: str,
    version: str,
    algorithm: str,
    params: dict[str, Any],
    metrics: dict[str, Any],
    mlflow_run_id: str,
    artifact_uri: str,
    trained_by: int | None,
    status: str = "staging",
    scope: str = "global",
) -> ModelRegistry:
    row = ModelRegistry(
        name=name,
        version=version,
        algorithm=algorithm,
        params=params,
        metrics=metrics,
        mlflow_run_id=mlflow_run_id,
        artifact_uri=artifact_uri,
        status=status,
        scope=scope,
        trained_by=trained_by,
    )
    db.add(row)
    db.flush()
    return row


def list_jobs(db: Session, *, offset: int, limit: int) -> tuple[list[TrainingJob], int]:
    total = db.query(TrainingJob).count()
    items = (
        db.query(TrainingJob)
        .order_by(TrainingJob.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total


def list_models(db: Session) -> list[ModelRegistry]:
    return db.query(ModelRegistry).order_by(ModelRegistry.id.desc()).all()


def get_model(db: Session, model_id: int) -> Optional[ModelRegistry]:
    return db.query(ModelRegistry).filter(ModelRegistry.id == model_id).first()


def get_production_model(
    db: Session, scope: str = "global", task: str | None = "classification"
) -> Optional[ModelRegistry]:
    rows = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.status == "production", ModelRegistry.scope == scope)
        .order_by(ModelRegistry.id.desc())
        .all()
    )
    if task is None:
        return rows[0] if rows else None
    for row in rows:
        row_task = (row.params or {}).get("task") or "classification"
        if row_task == task:
            return row
    return rows[0] if rows else None


def archive_production(
    db: Session, scope: str = "global", task: str | None = None
) -> int:
    rows = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.status == "production", ModelRegistry.scope == scope)
        .all()
    )
    n = 0
    for row in rows:
        if task is not None:
            row_task = (row.params or {}).get("task") or "classification"
            if row_task != task:
                continue
        row.status = "archived"
        db.add(row)
        n += 1
    db.flush()
    return n
