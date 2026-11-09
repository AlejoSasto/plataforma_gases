"""Guardias de cierre del Plan 25. Funciones puras, sin efectos."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def emission_allowed(train_end: datetime, embargo: timedelta, issued_at: datetime) -> bool:
    """Sin fuga: el modelo que pronostica t no vio t."""
    return train_end + embargo < issued_at


def anticipatory_allowed(
    issued_at: datetime,
    final_block_start: datetime | None,
    *,
    final_released: bool,
) -> bool:
    """El bloque final no recibe avisos anticipados hasta su corrida única."""
    if final_block_start is None or issued_at < final_block_start:
        return True
    return bool(final_released)


def historic_presented_as_open(origin: str, status: str) -> bool:
    return origin == "historico" and status == "abierta"


def should_email(origin: str) -> bool:
    return origin != "historico"


def lineage_complete(row: dict[str, Any]) -> bool:
    return bool(row.get("sensor_id")) and bool(row.get("source_file"))


def metrics_from_backtest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """model_evaluations se recalcula solo desde backtest_forecasts."""
    errs: list[float] = []
    for row in rows:
        y_true = row.get("y_true")
        q50 = row.get("q50")
        if y_true is None or q50 is None:
            continue
        errs.append(abs(float(y_true) - float(q50)))
    mae = sum(errs) / len(errs) if errs else None
    return {"n": len(errs), "mae": mae}


def reliability_counts(outcomes: list[dict[str, Any]]) -> dict[str, int]:
    timely = missed = unnecessary = 0
    for row in outcomes:
        label = str(row.get("outcome") or "").lower()
        if label in {"acertado", "acierto", "a_tiempo", "timely"}:
            timely += 1
        elif label in {"no_avisado", "omitido", "fn"}:
            missed += 1
        elif label in {"innecesario", "falsa", "fa"}:
            unnecessary += 1
    return {"timely": timely, "missed": missed, "unnecessary": unnecessary, "total": len(outcomes)}
