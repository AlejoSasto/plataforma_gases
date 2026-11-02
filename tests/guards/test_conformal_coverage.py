"""Cobertura conformal del intervalo [q10, q90] = 90 % ± 2 pp."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml_core.forecasting.conformal import ConformalCalibrator, coverage


@pytest.mark.plan17
def test_conformal_coverage() -> None:
    rng = np.random.default_rng(7)
    n = 4000
    y = np.cumsum(rng.normal(0.0, 1.0, n + 1))
    actual = y[1:]
    q_point = y[:-1]  # persistencia
    n_cal = 2500
    cal = ConformalCalibrator()
    cal.fit(
        actual[:n_cal],
        q_point[:n_cal],
        q_point[:n_cal],
        q_point[:n_cal],
        q_point[:n_cal],
        horizon_min=6,
    )
    pred = pd.DataFrame(
        {
            "horizon_min": np.full(n - n_cal, 6),
            "q10": q_point[n_cal:],
            "q50": q_point[n_cal:],
            "q90": q_point[n_cal:],
            "q95": q_point[n_cal:],
        }
    )
    out = cal.apply(pred)
    cov = coverage(actual[n_cal:], out["q10"].to_numpy(), out["q90"].to_numpy())
    assert abs(cov - 0.90) <= 0.02, f"cobertura {cov:.3f} fuera de 0.90 ± 0.02"
