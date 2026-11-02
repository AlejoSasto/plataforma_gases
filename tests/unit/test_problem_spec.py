import pytest

from ml_core.forecasting.problem import ProblemSpec, pinball_loss

pytestmark = pytest.mark.plan(15)


def test_problem_spec_from_g0() -> None:
    spec = ProblemSpec.from_g0({"horizons_min": [5, 10], "dt_p50_min_priority_max": 1.0})
    assert spec.horizons == (5, 10)
    assert spec.k_max == 10
    assert spec.purge_gap_steps == spec.lookback + 10


def test_pinball_asymmetric() -> None:
    # tau alto: subestimar cuesta más
    under = pinball_loss(10, 8, 0.95)
    over = pinball_loss(10, 12, 0.95)
    assert under > over
