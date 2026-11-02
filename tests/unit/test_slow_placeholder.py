"""Marca slow para la etapa 13 de verify.py --full."""

from __future__ import annotations

import pytest


@pytest.mark.slow
def test_slow_marker_present() -> None:
    assert True
