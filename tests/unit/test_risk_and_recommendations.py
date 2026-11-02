"""Recomendaciones por gas (umbrales de probabilidad retirados en Plan 23 F5)."""

from __future__ import annotations

from app.modules.alerts.recommendations import recommendation_for_gas


def test_recommendation_for_known_gas() -> None:
    assert "ventil" in recommendation_for_gas("CO").lower()
    assert recommendation_for_gas(None)
    assert recommendation_for_gas("gas desconocido xyz")
