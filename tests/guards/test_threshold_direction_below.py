import pytest

from ml_core.domain.thresholds import is_violation, levels_for_gas

pytestmark = pytest.mark.plan(15)


def test_threshold_direction_below() -> None:
    vigilar = [t for t in levels_for_gas("O2") if t.level == "vigilar"][0]
    assert vigilar.direction == "below"
    assert is_violation(19.0, vigilar)
    assert not is_violation(20.5, vigilar)
