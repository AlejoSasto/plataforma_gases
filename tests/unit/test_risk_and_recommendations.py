"""Tests unitarios de umbrales de riesgo y recomendaciones."""

from __future__ import annotations

from app.core.config import settings
from app.modules.alerts.recommendations import (
    probability_to_risk_level,
    recommendation_for_gas,
)


def test_probability_to_risk_level_thresholds() -> None:
    assert probability_to_risk_level(0.0) == "NORMAL"
    assert probability_to_risk_level(settings.risk_threshold_precaution) == "PRECAUCION"
    assert probability_to_risk_level(settings.risk_threshold_alert) == "ALERTA"
    assert probability_to_risk_level(settings.risk_threshold_critical) == "CRITICO"
    assert probability_to_risk_level(0.99) == "CRITICO"


def test_recommendations_by_gas() -> None:
    assert "ventil" in recommendation_for_gas("CO").lower()
    assert "evacuar" in recommendation_for_gas("O2").lower()
    lel = recommendation_for_gas("LEL").lower()
    assert "ignici" in lel
    assert len(recommendation_for_gas("UNKNOWN_XYZ")) > 0
