"""Plan 15 F0: intervalos, duplicados y G0 sobre un set de juguete."""

from __future__ import annotations

import pandas as pd
import pytest

from ml_core.diagnosis import duplicates_report, g0_decision, prepare_frame, run_diagnosis

pytestmark = pytest.mark.plan(15)


def _toy() -> pd.DataFrame:
    t0 = pd.Timestamp("2025-01-01T00:00:00Z")
    rows = []
    # CH4 cada 1 min, 20 puntos
    for i in range(20):
        rows.append(
            {
                "Sensor": "SN:AAA",
                "Gas": "CH4",
                "Leyendo": 0.2 + (0.01 if i == 10 else 0),
                "Unidad": "%vol",
                "Tiempo de Inicio": t0 + pd.Timedelta(minutes=i),
                "Sitio": "Frente",
            }
        )
    # duplicado exacto del primer punto
    rows.append(dict(rows[0]))
    return pd.DataFrame(rows)


def test_interval_p50_is_one_minute() -> None:
    report = run_diagnosis(_toy(), source="toy")
    ch4 = [s for s in report["sensors"] if s["gas"] == "CH4"][0]
    assert ch4["dt_p50_min"] == pytest.approx(1.0, abs=1e-6)
    assert ch4["n"] >= 20


def test_duplicates_detected() -> None:
    prepared = prepare_frame(_toy())
    dups = duplicates_report(prepared)
    assert dups["exact"] >= 1


def test_g0_fine_band_for_one_minute() -> None:
    report = run_diagnosis(_toy(), source="toy")
    assert report["g0"]["band"] == "fine"
    assert report["g0"]["horizons_min"] == [5, 10]


def test_g0_coarse_when_dt_large() -> None:
    rows = [
        {
            "sensor_code": "S1",
            "gas": "CH4",
            "dt_p50_min": 30.0,
        }
    ]
    g0 = g0_decision(rows)
    assert g0["band"] == "coarse"
    assert g0["horizons_min"] == [30, 60, 90]
