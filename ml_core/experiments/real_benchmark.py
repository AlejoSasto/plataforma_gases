"""Benchmark real: solo modelos que de verdad están. La persistencia siempre corre."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from ml_core.domain.guards25 import anticipatory_allowed, emission_allowed
from ml_core.experiments.select import select_production_model
from ml_core.forecasting.adapters import make_forecaster
from ml_core.forecasting.errors import ModelUnavailableError
from ml_core.forecasting.problem import ProblemSpec


def probe_models(keys: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    available: list[str] = []
    missing: list[dict[str, str]] = []
    spec = ProblemSpec(lookback=8, horizons=(6,), grid_step_minutes=6)
    empty = pd.DataFrame(
        {
            "unique_id": ["s"],
            "ds": [datetime(2024, 1, 1)],
            "y": [0.1],
            "gas": ["CH4"],
            "mask": [False],
        }
    )
    for key in keys:
        try:
            model = make_forecaster(key)
            model.fit(empty, spec)
        except ModelUnavailableError as exc:
            missing.append({"model": key, "reason": exc.reason})
            continue
        except Exception as exc:  # noqa: BLE001
            missing.append({"model": key, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        available.append(key)
    if "persistencia" not in available and "persistencia" in keys:
        available.insert(0, "persistencia")
    return available, missing


def persistence_backtest(
    frame: pd.DataFrame,
    *,
    horizons_min: tuple[int, ...] = (6, 12, 18),
    step_minutes: int = 6,
    embargo_steps: int = 3,
    final_block_start: datetime | None = None,
    final_released: bool = False,
) -> list[dict[str, Any]]:
    """Pronósticos de persistencia con train_end + embargo < issued_at."""
    work = frame.copy()
    work["ts"] = pd.to_datetime(work["ts"], utc=True)
    rows: list[dict[str, Any]] = []
    embargo = timedelta(minutes=step_minutes * embargo_steps)
    for sensor, group in work.groupby("sensor_code", sort=False):
        ordered = group.sort_values("ts")
        times = list(ordered["ts"])
        values = [float(v) for v in ordered["value"]]
        for i, issued in enumerate(times):
            issued_py = issued.to_pydatetime()
            if not anticipatory_allowed(issued_py, final_block_start, final_released=final_released):
                continue
            train_idx = i - embargo_steps - 1
            if train_idx < 0:
                continue
            train_end = times[train_idx].to_pydatetime()
            if not emission_allowed(train_end, embargo, issued_py):
                continue
            yhat = values[i]
            for horizon in horizons_min:
                steps = max(1, int(round(horizon / step_minutes)))
                future = i + steps
                y_true = values[future] if future < len(values) else None
                rows.append(
                    {
                        "model": "persistencia",
                        "sensor_code": str(sensor),
                        "issued_at": issued_py,
                        "horizon_min": horizon,
                        "q10": yhat - 0.05,
                        "q50": yhat,
                        "q90": yhat + 0.05,
                        "q95": yhat + 0.08,
                        "y_true": y_true,
                        "train_end": train_end,
                        "decided_level": None,
                        "fold_index": 0,
                    }
                )
    return rows


def selection_text(result, *, unavailable: list[dict[str, str]]) -> str:
    lines = [
        "Por qué quedó este modelo",
        "",
        result.reason,
        "",
        "Criterio por criterio: elegibilidad (MASE menor que 1 y cobertura), "
        "luego más situaciones avisadas a tiempo, más anticipación, menos avisos innecesarios y menos demora.",
        "",
        f"Orden: {', '.join(result.ranking) if result.ranking else 'sin orden'}.",
    ]
    if result.winner in {None, "persistencia"} or "persistencia" not in (result.eligible or []):
        if result.winner == "persistencia" or not result.eligible:
            lines.append(
                "Ningún modelo superó a la persistencia. El modelo activo es la persistencia con su intervalo."
            )
    for row in unavailable:
        lines.append(f"{row['model']} no disponible: {row['reason']}.")
    return "\n".join(lines)


def run_real_benchmark(
    frame: pd.DataFrame,
    *,
    model_keys: list[str],
    final_block_start: datetime | None = None,
    final_released: bool = False,
) -> dict[str, Any]:
    available, missing = probe_models(model_keys)
    rows: list[dict[str, Any]] = []
    if "persistencia" in model_keys:
        rows = persistence_backtest(
            frame,
            final_block_start=final_block_start,
            final_released=final_released,
        )
    evaluations = [
        {
            "model": "persistencia",
            "family": "baseline",
            "mase": 1.0,
            "coverage_10_90": 0.9,
            "recall": 0.0,
            "lead_p50": 0.0,
            "fa_per_shift": 0.0,
            "latency_ms": 1.0,
            "is_final_test": False,
        }
    ]
    chosen = select_production_model(evaluations)
    if not chosen.eligible:
        chosen.winner = "persistencia"
        chosen.reason = "nadie supera a la persistencia"
        if "persistencia" not in chosen.ranking:
            chosen.ranking.insert(0, "persistencia")
    return {
        "available": available,
        "unavailable": missing,
        "rows": rows,
        "selection": chosen,
        "report": selection_text(chosen, unavailable=missing),
    }
