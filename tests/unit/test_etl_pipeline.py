"""Plan 15 F2: etapas ETL puras."""

from __future__ import annotations

import pandas as pd
import pytest

from app.modules.ingestion.pipeline.e2_validate import e2_validate
from app.modules.ingestion.pipeline.e3_standardize import e3_standardize
from app.modules.ingestion.pipeline.e6_grid import e6_grid
from ml_core.columns import EXPECTED_COLUMNS
from ml_core.domain.units import to_canonical

pytestmark = pytest.mark.plan(15)


def _frame(**overrides) -> pd.DataFrame:
    base = {c: None for c in EXPECTED_COLUMNS}
    base.update(
        {
            "Sensor": "Sensor SN: XYZ",
            "Gas": "LEL(CH4)",
            "Leyendo": 10.0,
            "Unidad": "%lel",
            "Tiempo de Inicio": pd.Timestamp("2025-01-01T00:00:00Z"),
            "Sitio": "",
            "Descripción": "Gas combustible",
        }
    )
    base.update(overrides)
    return pd.DataFrame([base])


def test_lel_to_percent_vol() -> None:
    v, u = to_canonical(10.0, gas_code="CH4", unit="%lel")
    assert u == "%vol"
    assert v == pytest.approx(0.5)  # 10% LEL * 5.0/100


def test_e3_converts_lel() -> None:
    s = e3_standardize(_frame())
    assert s.dataframe.iloc[0]["gas"] == "CH4"
    assert s.dataframe.iloc[0]["value_canonical"] == pytest.approx(0.5)
    assert s.details["conversions"] >= 1


def test_e2_rejects_bad_reading() -> None:
    df = _frame(Leyendo="no-num")
    s = e2_validate(df)
    assert s.rows_rejected == 1
    assert s.rows_out == 0


def test_grid_does_not_invent_long_gaps() -> None:
    t0 = pd.Timestamp("2025-01-01T00:00:00Z")
    df = pd.DataFrame(
        {
            "sensor_code": ["S", "S"],
            "gas": ["CH4", "CH4"],
            "value_canonical": [1.0, 2.0],
            "Tiempo de Inicio": [t0, t0 + pd.Timedelta(minutes=10)],
        }
    )
    grid = e6_grid(df, step_minutes=1, max_impute_steps=3)
    # 11 puntos (0..10). El hueco largo no se rellena entero.
    missing = int(grid.dataframe["is_missing"].sum())
    imputed = int(grid.dataframe["is_imputed"].sum())
    assert missing >= 4
    assert imputed <= 3
    # ningún valor imputado viene del futuro: el primer punto sigue 1.0
    first = grid.dataframe.iloc[0]
    assert first["value"] == pytest.approx(1.0)
