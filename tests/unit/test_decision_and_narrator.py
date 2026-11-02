"""Decisión, histéresis y narrador (Plan 17)."""

from __future__ import annotations

import numpy as np
import pytest

from ml_core.domain.thresholds import levels_for_gas
from ml_core.forecasting.decision import (
    DecisionState,
    confirmed_level,
    exceedance_probability,
    fit_decision_threshold,
    operational_level,
    probs_for_horizon,
)
from ml_core.forecasting.explain.factors import FACTOR_CODES, heuristic_factors
from ml_core.forecasting.explain.language import forbidden_in
from ml_core.forecasting.explain.narrator import TEMPLATES, narrate, templates_cover_catalog
from ml_core.forecasting.problem import ProblemSpec
from ml_core.forecasting.serve import NO_MODEL_MESSAGE, infer_sensor


@pytest.mark.plan17
def test_templates_cover_factors() -> None:
    templates_cover_catalog()
    assert set(TEMPLATES) == set(FACTOR_CODES)


@pytest.mark.plan17
def test_narrator_plain_language() -> None:
    factors = heuristic_factors(
        np.array([0.2, 0.4, 0.8, 1.1]),
        gas="CH4",
        specs=levels_for_gas("CH4"),
        step_minutes=6,
        other_gas_rising=True,
        temperature_rising=True,
        hour=18,
    )
    text = narrate(factors)
    assert forbidden_in(text) == []
    assert "metano" in text.lower() or "límite" in text.lower() or "aumento" in text.lower()


@pytest.mark.plan17
def test_persistence_and_hysteresis() -> None:
    state = DecisionState(persistence_steps=2, hysteresis=0.8, pi={"vigilar": 0.4, "actuar": 0.5, "evacuar": 0.8})
    assert state.update({"vigilar": 0.9, "actuar": 0.6, "evacuar": 0.1}) == "normal"
    assert state.update({"vigilar": 0.9, "actuar": 0.6, "evacuar": 0.1}) == "actuar"
    # histéresis: baja un poco pero sigue sobre 0.8 * 0.5
    assert state.update({"vigilar": 0.3, "actuar": 0.42, "evacuar": 0.0}) == "actuar"
    assert state.update({"vigilar": 0.1, "actuar": 0.1, "evacuar": 0.0}) == "normal"


@pytest.mark.plan17
def test_confirmed_independent_of_model() -> None:
    specs = levels_for_gas("CH4")
    assert confirmed_level(1.7, specs) == "evacuar"
    assert confirmed_level(0.2, specs) is None
    ctx = __import__("pandas").DataFrame({"unique_id": ["S"], "ds": [__import__("pandas").Timestamp("2024-01-01", tz="UTC")], "y": [1.7]})
    spec = ProblemSpec(lookback=4, horizons=(6,), grid_step_minutes=6)
    result = infer_sensor(ctx, spec, gas="CH4", model=None, last_value=1.7)
    assert result.kind == "confirmado"
    assert result.status_level == "evacuar"
    assert result.confirmed_only
    none = infer_sensor(ctx, spec, gas="CH4", model=None, last_value=0.1)
    assert none.plain_text == NO_MODEL_MESSAGE


@pytest.mark.plan17
def test_operational_level_max() -> None:
    assert operational_level("vigilar", "evacuar") == "evacuar"
    assert operational_level("evacuar", "normal") == "evacuar"


@pytest.mark.plan17
def test_exceedance_and_empty_threshold() -> None:
    assert exceedance_probability(q10=1, q50=2, q90=3, q95=4, threshold=0.5, direction="above") > 0.5
    assert exceedance_probability(q10=1, q50=2, q90=3, q95=4, threshold=10, direction="above") < 0.2
    below = exceedance_probability(q10=18, q50=19, q90=20, q95=21, threshold=19.5, direction="below")
    assert 0.0 <= below <= 1.0
    empty = fit_decision_threshold(np.array([]), np.array([]), fa_per_shift_max=1, shift_hours=8, step_minutes=6)
    assert empty["pi"] == 0.5
    scores = np.array([0.1, 0.9, 0.8, 0.2])
    event = np.array([0, 1, 1, 0])
    fitted = fit_decision_threshold(scores, event, fa_per_shift_max=2.0, shift_hours=8, step_minutes=6)
    assert "pi" in fitted
    specs = levels_for_gas("O2")
    probs = probs_for_horizon(20.5, 20.0, 19.2, 18.8, specs)
    assert "vigilar" in probs
    nan = exceedance_probability(
        q10=float("nan"), q50=float("nan"), q90=float("nan"), q95=float("nan"), threshold=1.0, direction="above"
    )
    assert nan == 0.5
    unconstrained = fit_decision_threshold(
        np.ones(12),
        np.zeros(12, dtype=int),
        fa_per_shift_max=1e-6,
        shift_hours=8,
        step_minutes=6,
    )
    assert unconstrained["constrained"] is False
