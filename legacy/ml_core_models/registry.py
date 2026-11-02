"""Catálogo del Model Zoo (matriz thesis)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Family = Literal["tabular", "sequence"]
Task = Literal["classification", "regression", "both"]


@dataclass(frozen=True)
class ModelSpec:
    algorithm: str
    family: Family
    label: str
    architecture: str
    tasks: tuple[Task, ...]
    # Métricas clave aplicables
    uses_recall: bool = True
    uses_precision: bool = True
    uses_f1: bool = True
    uses_rmse: bool = False
    uses_lead: bool = False
    uses_fn: bool = True
    framework: str = "sklearn"


MODEL_CATALOG: dict[str, ModelSpec] = {
    "logistic_regression": ModelSpec(
        "logistic_regression",
        "tabular",
        "Regresión logística",
        "Clasificación lineal (baseline)",
        ("classification",),
        framework="sklearn",
    ),
    "decision_tree": ModelSpec(
        "decision_tree",
        "tabular",
        "Árboles de decisión",
        "Modelo lógico / reglas",
        ("classification",),
        uses_rmse=False,
        uses_lead=False,
        framework="sklearn",
    ),
    "random_forest": ModelSpec(
        "random_forest",
        "tabular",
        "Random Forest",
        "Ensamble de árboles",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=False,
        framework="sklearn",
    ),
    "xgboost": ModelSpec(
        "xgboost",
        "tabular",
        "XGBoost",
        "Gradient boosting",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=False,
        framework="xgboost",
    ),
    "svm": ModelSpec(
        "svm",
        "tabular",
        "SVM",
        "Clasificación / anomalías",
        ("classification",),
        uses_rmse=False,
        uses_lead=False,
        framework="sklearn",
    ),
    "mlp": ModelSpec(
        "mlp",
        "tabular",
        "MLP (sklearn)",
        "Red neuronal densa tabular",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=False,
        framework="sklearn",
    ),
    "lstm": ModelSpec(
        "lstm",
        "sequence",
        "LSTM",
        "RNN / series temporales",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=True,
        framework="torch",
    ),
    "gru": ModelSpec(
        "gru",
        "sequence",
        "GRU",
        "RNN gated / series temporales",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=True,
        framework="torch",
    ),
    "transformer": ModelSpec(
        "transformer",
        "sequence",
        "Transformer",
        "Atención temporal",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=True,
        framework="torch",
    ),
    "cnn1d": ModelSpec(
        "cnn1d",
        "sequence",
        "CNN 1D",
        "Convolución temporal + MLP",
        ("classification", "regression", "both"),
        uses_rmse=True,
        uses_lead=True,
        framework="torch",
    ),
}

DEFAULT_TABULAR = [
    "logistic_regression",
    "decision_tree",
    "random_forest",
    "svm",
    "mlp",
    "xgboost",
]
DEFAULT_SEQUENCE = ["lstm", "gru", "transformer", "cnn1d"]
DEFAULT_ALL = DEFAULT_TABULAR + DEFAULT_SEQUENCE


def get_spec(algorithm: str) -> ModelSpec:
    key = algorithm.lower().strip()
    if key not in MODEL_CATALOG:
        raise KeyError(f"Algoritmo desconocido: {algorithm}")
    return MODEL_CATALOG[key]


def applicability_for(algorithm: str, task: str) -> dict[str, bool]:
    spec = get_spec(algorithm)
    wants_reg = task in ("regression", "both")
    wants_clf = task in ("classification", "both")
    return {
        "recall": wants_clf and spec.uses_recall,
        "precision": wants_clf and spec.uses_precision,
        "f1": wants_clf and spec.uses_f1,
        "fn": wants_clf and spec.uses_fn,
        "rmse": wants_reg and spec.uses_rmse,
        "lead": wants_clf and spec.uses_lead,
    }


def catalog_public() -> list[dict]:
    rows = []
    for spec in MODEL_CATALOG.values():
        rows.append(
            {
                "algorithm": spec.algorithm,
                "family": spec.family,
                "label": spec.label,
                "architecture": spec.architecture,
                "tasks": list(spec.tasks),
                "framework": spec.framework,
                "metrics": {
                    "recall": spec.uses_recall,
                    "precision": spec.uses_precision,
                    "f1": spec.uses_f1,
                    "rmse": spec.uses_rmse,
                    "lead": spec.uses_lead,
                    "fn": spec.uses_fn,
                },
            }
        )
    return rows
