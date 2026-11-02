"""Contraste WCAG 2.2 AA de tokens de estado (Plan 18)."""

from __future__ import annotations

import pytest

from app.shared.design_tokens import LIGHT, SALA, STATUS, contrast_ratio


@pytest.mark.plan18
def test_status_soft_text_aa() -> None:
    for name, colors in STATUS.items():
        ratio = contrast_ratio(colors["text"], colors["soft"])
        assert ratio >= 4.5, f"{name} texto/fondo suave = {ratio:.2f}"


@pytest.mark.plan18
def test_body_text_on_surfaces() -> None:
    assert contrast_ratio(LIGHT["text"], LIGHT["bg"]) >= 4.5
    assert contrast_ratio(LIGHT["text"], LIGHT["surface"]) >= 4.5
    assert contrast_ratio(LIGHT["text-2"], LIGHT["surface"]) >= 4.5
    assert contrast_ratio(SALA["text"], SALA["bg"]) >= 4.5
    assert contrast_ratio(SALA["text"], SALA["surface"]) >= 4.5
    assert contrast_ratio(SALA["accent"], SALA["bg"]) >= 4.5
