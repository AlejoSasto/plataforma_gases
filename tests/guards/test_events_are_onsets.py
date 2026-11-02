import pytest

from ml_core.domain.events import forecast_onset_labels
from ml_core.domain.thresholds import levels_for_gas

pytestmark = pytest.mark.plan(15)


def test_events_are_onsets() -> None:
    spec = [t for t in levels_for_gas("CO") if t.level == "vigilar"][0]
    # 30 ppm umbral 25: episodio en curso en t=0
    vals = [30.0, 31.0, 10.0, 40.0]
    labels = forecast_onset_labels(vals, spec, k_max_steps=2)
    assert labels[0] == 0
    assert labels[2] == 1
