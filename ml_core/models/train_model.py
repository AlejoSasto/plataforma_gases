"""Orquestador del Model Zoo: selecciona algoritmos y dispara tabular / sequence."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional

import mlflow
from sqlalchemy.orm import Session

from app.core.config import settings
from ml_core.models.registry import DEFAULT_ALL, DEFAULT_SEQUENCE, DEFAULT_TABULAR, get_spec
from ml_core.models.train_sequence import train_sequence_algorithms
from ml_core.models.train_tabular import TrainingResult, train_tabular_algorithms


def train(
    db: Session,
    *,
    dataset_version: str = "gas_readings",
    params: Optional[dict[str, Any]] = None,
    triggered_by_user_id: int | None = None,
) -> list[TrainingResult]:
    """
    Entrena el subset solicitado.
    params:
      algorithms: list[str] | None  (default: todos tabulares; 'all' = todos)
      task: classification | regression | both
      max_rows, test_months, lookback_steps, horizon_minutes, epochs, tracking_uri
    """
    params = dict(params or {})
    tracking_uri = params.pop("tracking_uri", None) or settings.mlflow_tracking_uri
    task = str(params.get("task") or "classification").lower()
    if task not in ("classification", "regression", "both"):
        task = "classification"

    raw_algos = params.get("algorithms")
    if raw_algos is None or raw_algos == []:
        algorithms = list(DEFAULT_TABULAR)
    elif raw_algos == "all" or raw_algos == ["all"]:
        algorithms = list(DEFAULT_ALL)
    elif isinstance(raw_algos, str):
        algorithms = [a.strip() for a in raw_algos.split(",") if a.strip()]
    else:
        algorithms = [str(a).strip() for a in raw_algos]

    # Validar
    normalized: list[str] = []
    for a in algorithms:
        get_spec(a)
        normalized.append(a.lower())

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("plataforma-gases-training")

    tabular = [a for a in normalized if get_spec(a).family == "tabular"]
    sequence = [a for a in normalized if get_spec(a).family == "sequence"]

    results: list[TrainingResult] = []
    train_params = {
        k: v
        for k, v in params.items()
        if k
        not in (
            "algorithms",
            "task",
        )
    }
    train_params["task"] = task

    if tabular:
        results.extend(
            train_tabular_algorithms(
                db,
                tabular,
                task=task if task != "regression" else "regression",
                dataset_version=dataset_version,
                params=train_params,
                triggered_by_user_id=triggered_by_user_id,
            )
        )
    if sequence:
        # DL por defecto both para aprovechar RMSE + lead; si el usuario pide classification, respetar
        seq_task = task if task != "classification" else "both"
        if task == "classification":
            seq_task = "classification"
        results.extend(
            train_sequence_algorithms(
                db,
                sequence,
                task=seq_task if task != "regression" else "regression",
                dataset_version=dataset_version,
                params=train_params,
                triggered_by_user_id=triggered_by_user_id,
            )
        )

    if not results:
        raise ValueError("Ningún algoritmo produjo resultados (revisa task/algorithms/datos)")
    return results


def best_result(results: list[TrainingResult]) -> TrainingResult:
    def score(r: TrainingResult) -> tuple:
        m = r.metrics or {}
        gates = m.get("gates") or {}
        return (
            1 if gates.get("meets_thesis") else 0,
            m.get("f1") or 0.0,
            m.get("recall") or 0.0,
            -(m.get("rmse") or 1e9),
        )

    return max(results, key=score)


def result_to_dict(result: TrainingResult) -> dict[str, Any]:
    data = asdict(result)
    data.pop("model", None)
    return data


# Re-export helpers usados por UI
__all__ = [
    "TrainingResult",
    "train",
    "best_result",
    "result_to_dict",
    "DEFAULT_ALL",
    "DEFAULT_TABULAR",
    "DEFAULT_SEQUENCE",
]
