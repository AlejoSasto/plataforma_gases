"""Alterar el futuro no cambia rasgos en t (Plan 20 F3)."""

from __future__ import annotations

import numpy as np
import pytest

from ml_core.forecasting.adapters._common import lookback_matrix

pytestmark = pytest.mark.plan(15)


def test_features_are_causal() -> None:
    y = np.linspace(0.1, 2.0, 40)
    lookback, h = 8, 2
    x_a, _ = lookback_matrix(y, lookback, h)
    y_b = y.copy()
    y_b[20:] = y_b[20:] + 50.0
    x_b, _ = lookback_matrix(y_b, lookback, h)
    for i, t in enumerate(range(lookback, 20)):
        del t
        np.testing.assert_allclose(x_a[i], x_b[i])
