"""Catálogo de factores comprensibles (Plan 17 §6)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ml_core.domain.thresholds import ThresholdSpec, is_violation

FACTOR_CODES: tuple[str, ...] = (
    "tendencia_subida",
    "nivel_alto",
    "subida_brusca",
    "otro_gas",
    "temperatura",
    "hora_turno",
)

GAS_PLAIN = {
    "CH4": "metano",
    "CO": "monóxido de carbono",
    "H2S": "sulfuro de hidrógeno",
    "O2": "oxígeno",
    "CO2": "dióxido de carbono",
    "NO2": "dióxido de nitrógeno",
}


def heuristic_factors(
    window: np.ndarray,
    *,
    gas: str = "CH4",
    specs: list[ThresholdSpec] | None = None,
    step_minutes: int = 6,
    other_gas_rising: bool = False,
    temperature_rising: bool = False,
    hour: int | None = None,
) -> list[dict[str, Any]]:
    """Factores a partir de la ventana (método por oclusión/heurística, sin jerga)."""
    y = np.asarray(window, dtype=float)
    y = y[np.isfinite(y)]
    if y.size < 3:
        return []
    factors: list[dict[str, Any]] = []
    n_min = int((y.size - 1) * step_minutes)
    slope = float(y[-1] - y[0]) / max(n_min, 1)
    if slope > 0:
        factors.append(
            {
                "factor_code": "tendencia_subida",
                "weight": min(1.0, abs(slope) * 4),
                "direction": "up",
                "gas": GAS_PLAIN.get(gas, gas),
                "n": max(step_minutes, n_min),
            }
        )
    jump = float(y[-1] - y[-2])
    if jump > np.std(y) * 0.8 and jump > 0:
        factors.append(
            {
                "factor_code": "subida_brusca",
                "weight": min(1.0, abs(jump)),
                "direction": "up",
                "n": int(step_minutes),
            }
        )
    if specs:
        last = float(y[-1])
        nearest = None
        nearest_level = None
        for spec in specs:
            dist = abs(last - float(spec.value))
            if nearest is None or dist < nearest:
                nearest = dist
                nearest_level = spec.level
            if is_violation(last, spec) or dist / max(abs(spec.value), 1e-6) < 0.25:
                factors.append(
                    {
                        "factor_code": "nivel_alto",
                        "weight": 0.9,
                        "direction": "up" if spec.direction == "above" else "down",
                        "nivel": spec.level,
                    }
                )
                break
        del nearest_level
    if other_gas_rising:
        factors.append(
            {
                "factor_code": "otro_gas",
                "weight": 0.45,
                "direction": "up",
                "otro_gas": "otro gas de la misma zona",
            }
        )
    if temperature_rising:
        factors.append({"factor_code": "temperatura", "weight": 0.35, "direction": "up"})
    if hour is not None and hour in {5, 6, 7, 17, 18, 19}:
        factors.append({"factor_code": "hora_turno", "weight": 0.25, "direction": "up"})
    factors.sort(key=lambda r: float(r["weight"]), reverse=True)
    return factors[:3]
