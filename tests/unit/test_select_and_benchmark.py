"""Selección sin preferencia de familia, benchmark reducido y latencia."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from ml_core.experiments.run_benchmark import run_benchmark
from ml_core.experiments.select import select_production_model
from ml_core.experiments.thesis_report import generate
from ml_core.forecasting.adapters import make_forecaster
from ml_core.forecasting.problem import ProblemSpec


@pytest.mark.plan17
def test_select_no_family_preference() -> None:
    rows = [
        {
            "model": "tft",
            "family": "transformer",
            "mase": 0.7,
            "coverage_10_90": 0.90,
            "recall": 0.40,
            "lead_p50": 12.0,
            "fa_per_shift": 0.2,
            "latency_ms": 10.0,
            "is_final_test": False,
        },
        {
            "model": "persistencia",
            "family": "baseline",
            "mase": 0.8,
            "coverage_10_90": 0.91,
            "recall": 0.80,
            "lead_p50": 6.0,
            "fa_per_shift": 0.4,
            "latency_ms": 1.0,
            "is_final_test": False,
        },
        {
            "model": "solo-final",
            "family": "transformer",
            "mase": 0.1,
            "coverage_10_90": 0.90,
            "recall": 0.99,
            "is_final_test": True,
        },
    ]
    result = select_production_model(rows)
    assert result.winner == "persistencia"
    assert "solo-final" not in result.ranking
    assert "tft" in result.ranking


@pytest.mark.plan17
def test_reduced_benchmark_and_report(tmp_path) -> None:
    start = datetime(2024, 4, 1, tzinfo=timezone.utc)
    n = 160
    rng = np.random.default_rng(11)
    df = pd.DataFrame(
        {
            "sensor_code": "S1",
            "ts": [start + timedelta(minutes=6 * i) for i in range(n)],
            "value": 0.35 + np.cumsum(rng.normal(0, 0.008, n)),
            "gas": "CH4",
        }
    )
    spec = ProblemSpec(lookback=8, horizons=(6, 12, 18), grid_step_minutes=6)
    rows = run_benchmark(df, spec, models=["persistencia"])
    assert rows
    dest = generate(rows, out_dir=tmp_path)
    assert (dest / "metricas.md").exists()
    assert (dest / "metricas.tex").exists()
    assert (dest / "ablaciones.md").exists()


@pytest.mark.plan17
def test_latency_under_one_second() -> None:
    spec = ProblemSpec(lookback=8, horizons=(6, 12, 18), grid_step_minutes=6)
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    model = make_forecaster("persistencia")
    train = pd.DataFrame(
        {
            "unique_id": ["S0"] * 40,
            "ds": [start + timedelta(minutes=6 * i) for i in range(40)],
            "y": np.linspace(0.2, 0.5, 40),
            "gas": ["CH4"] * 40,
            "mask": [False] * 40,
        }
    )
    model.fit(train, spec)
    frames = []
    for s in range(40):
        frames.append(
            pd.DataFrame(
                {
                    "unique_id": [f"S{s}"] * 8,
                    "ds": [start + timedelta(minutes=6 * i) for i in range(8)],
                    "y": np.linspace(0.2, 0.4, 8),
                    "gas": ["CH4"] * 8,
                    "mask": [False] * 8,
                }
            )
        )
    ctx = pd.concat(frames, ignore_index=True)
    t0 = time.perf_counter()
    pred = model.predict_quantiles(ctx, spec)
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"latencia {elapsed:.3f}s ≥ 1s"
    assert len(pred) >= 40
