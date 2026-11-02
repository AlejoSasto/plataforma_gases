"""Benchmark del zoo sobre walk-forward. Siempre incluye persistencia."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ml_core.forecasting.adapters import ADAPTERS, make_forecaster
from ml_core.forecasting.base import assert_prediction_frame
from ml_core.forecasting.dataset import to_long
from ml_core.forecasting.problem import ProblemSpec
from ml_core.validation.metrics import forecast_metrics
from ml_core.validation.walk_forward import walk_forward_folds

ROOT = Path(__file__).resolve().parents[2]


def _rolling_pairs(
    model,
    hist: pd.DataFrame,
    val: pd.DataFrame,
    spec: ProblemSpec,
    *,
    max_points: int = 24,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Pronóstico de un paso sobre validación: el contexto nunca ve el futuro."""
    h0 = int(spec.horizons[0])
    ys, q10s, q50s, q90s, pers = [], [], [], [], []
    hist = hist.copy()
    n = len(val)
    step = max(1, n // max_points)
    for i in range(0, n, step):
        ctx = hist.tail(max(spec.lookback, 2))
        if ctx.empty:
            break
        pred = model.predict_quantiles(ctx, spec)
        sub = pred[pred["horizon_min"] == h0]
        if sub.empty:
            continue
        row = sub.iloc[0]
        actual = float(pd.to_numeric(val.iloc[i]["y"], errors="coerce"))
        persist = float(pd.to_numeric(ctx["y"], errors="coerce").dropna().iloc[-1])
        ys.append(actual)
        q10s.append(float(row["q10"]))
        q50s.append(float(row["q50"]))
        q90s.append(float(row["q90"]))
        pers.append(persist)
        hist = pd.concat([hist, val.iloc[i : i + 1]], ignore_index=True)
    return (
        np.asarray(ys),
        np.asarray(q10s),
        np.asarray(q50s),
        np.asarray(q90s),
        np.asarray(pers),
    )


def evaluate_model(
    key: str,
    long: pd.DataFrame,
    spec: ProblemSpec,
    *,
    folds,
    include_final: bool = False,
) -> list[dict]:
    rows: list[dict] = []
    for fold in folds:
        if fold.is_final_test and not include_final:
            continue
        if fold.is_final_test:
            continue
        train = long.iloc[list(fold.train_idx)]
        calib = long.iloc[list(fold.calib_idx)] if fold.calib_idx else train.tail(8)
        val = long.iloc[list(fold.val_idx)]
        if train.empty or val.empty:
            continue
        model = make_forecaster(key)
        t0 = time.perf_counter()
        fit_frame = pd.concat([train, calib], ignore_index=True)
        model.fit(fit_frame, spec)
        smoke = model.predict_quantiles(fit_frame.tail(max(spec.lookback, 2)), spec)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        assert_prediction_frame(smoke)
        y, q10, q50, q90, persist = _rolling_pairs(model, fit_frame, val, spec)
        m = forecast_metrics(y, q10, q50, q90, persist)
        rows.append(
            {
                "model": key,
                "family": model.family,
                "backend": getattr(model, "backend", ""),
                "fold": fold.name,
                "is_final_test": bool(fold.is_final_test),
                "latency_ms": float(latency_ms),
                **m,
            }
        )
    return rows


def run_benchmark(
    frame: pd.DataFrame,
    spec: ProblemSpec,
    *,
    models: list[str] | None = None,
    include_final: bool = False,
) -> list[dict]:
    long = to_long(frame)
    long = long.sort_values("ds").reset_index(drop=True)
    folds = walk_forward_folds(
        long["ds"],
        lookback=spec.lookback,
        k_max=spec.k_max,
        min_val_steps=max(20, spec.lookback),
    )
    keys = models or list(ADAPTERS)
    if "persistencia" not in keys:
        keys = ["persistencia", *keys]
    out: list[dict] = []
    for key in keys:
        out.extend(evaluate_model(key, long, spec, folds=folds, include_final=include_final))
    return out


def _default_frame() -> pd.DataFrame:
    path = ROOT / "data" / "processed" / "dls_report_consolidado.csv"
    if path.exists():
        df = pd.read_csv(path)
        return df.head(800)
    rng = np.random.default_rng(17)
    n = 240
    ts = pd.date_range("2024-01-01", periods=n, freq="6min", tz="UTC")
    y = 0.3 + np.cumsum(rng.normal(0, 0.02, n))
    return pd.DataFrame({"sensor_code": "S1", "ts": ts, "value": y, "gas": "CH4"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="persistencia,ets,lgbm_q")
    parser.add_argument("--final-test", action="store_true")
    parser.add_argument("--lookback", type=int, default=12)
    args = parser.parse_args()
    spec = ProblemSpec(lookback=args.lookback, horizons=(6, 12, 18), grid_step_minutes=6)
    keys = [k.strip() for k in args.models.split(",") if k.strip()]
    rows = run_benchmark(_default_frame(), spec, models=keys, include_final=args.final_test)
    out = ROOT / "reports" / "thesis" / "benchmark.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {out} ({len(rows)} filas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
