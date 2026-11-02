import pytest

from ml_core.domain.events import count_onset_episodes, forecast_onset_labels
from ml_core.domain.thresholds import is_violation, levels_for_gas

pytestmark = pytest.mark.plan(15)


def test_oxygen_direction_below() -> None:
    o2 = [t for t in levels_for_gas("O2") if t.level == "evacuar"][0]
    assert o2.direction == "below"
    assert is_violation(16.0, o2)
    assert not is_violation(20.0, o2)


def test_onsets_ignore_ongoing_episode() -> None:
    spec = [t for t in levels_for_gas("CH4") if t.level == "vigilar"][0]
    # cruza en t=2, se mantiene alta, baja, cruza otra vez
    vals = [0.1, 0.2, 0.6, 0.7, 0.8, 0.2, 0.9]
    assert count_onset_episodes(vals, spec) == 2


def test_forecast_onset_excludes_already_in_event() -> None:
    spec = [t for t in levels_for_gas("CH4") if t.level == "vigilar"][0]
    vals = [0.1, 0.6, 0.7]
    labels = forecast_onset_labels(vals, spec, k_max_steps=2)
    assert labels[1] == 0  # ya en superación
    assert labels[0] == 1  # cruzará
