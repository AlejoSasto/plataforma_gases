"""Rendimiento local (Plan 20 F2 etapa 12)."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.modules.users.models import User
from ml_core.forecasting.adapters.baselines import PersistenceForecaster
from ml_core.forecasting.problem import ProblemSpec

pytestmark = pytest.mark.perf


def test_home_p95_under_300ms(client: TestClient, admin_user: tuple[User, str]) -> None:
    admin, password = admin_user
    assert client.post("/auth/login", json={"email": admin.email, "password": password}).status_code == 200
    client.get("/")
    times: list[float] = []
    for _ in range(12):
        t0 = time.perf_counter()
        res = client.get("/")
        times.append(time.perf_counter() - t0)
        assert res.status_code == 200
    p95 = float(np.percentile(times, 95))
    assert p95 < 0.3, f"p95 / = {p95:.3f}s"


def test_forecast_all_sensors_under_1s() -> None:
    spec = ProblemSpec(lookback=8, horizons=(6, 12, 18), grid_step_minutes=6)
    n = 40
    frame = pd.DataFrame(
        {
            "unique_id": np.repeat([f"s{i}" for i in range(12)], n),
            "ds": pd.date_range("2024-01-01", periods=n, freq="6min").tolist() * 12,
            "y": np.linspace(0.2, 0.8, n * 12),
        }
    )
    model = PersistenceForecaster()
    t0 = time.perf_counter()
    model.fit(frame, spec)
    model.predict_quantiles(frame, spec)
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0, f"pronóstico {elapsed:.3f}s"
