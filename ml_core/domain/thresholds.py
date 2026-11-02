"""Umbrales normativos semilla (verified=false hasta confirmar el artículo).

Valores iniciales del Plan 15 F4. Decreto 1886 de 2015 — a verificar
con el artículo exacto antes de usarlos en la tesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ThresholdLevel = Literal["vigilar", "actuar", "evacuar"]
Direction = Literal["above", "below"]


@dataclass(frozen=True)
class ThresholdSpec:
    gas_code: str
    level: ThresholdLevel
    direction: Direction
    value: float
    unit: str
    source_reference: str
    verified: bool = False


_DECRETO = "Decreto 1886 de 2015 (artículo a confirmar; verified=false)"

THRESHOLD_SEED: tuple[ThresholdSpec, ...] = (
    ThresholdSpec("CH4", "vigilar", "above", 0.5, "%vol", _DECRETO),
    ThresholdSpec("CH4", "actuar", "above", 1.0, "%vol", _DECRETO),
    ThresholdSpec("CH4", "evacuar", "above", 1.5, "%vol", _DECRETO),
    ThresholdSpec("CO", "vigilar", "above", 25.0, "ppm", _DECRETO),
    ThresholdSpec("CO", "actuar", "above", 50.0, "ppm", _DECRETO),
    ThresholdSpec("CO", "evacuar", "above", 100.0, "ppm", _DECRETO),
    ThresholdSpec("H2S", "vigilar", "above", 1.0, "ppm", _DECRETO),
    ThresholdSpec("H2S", "actuar", "above", 5.0, "ppm", _DECRETO),
    ThresholdSpec("H2S", "evacuar", "above", 10.0, "ppm", _DECRETO),
    ThresholdSpec("O2", "vigilar", "below", 19.5, "%vol", _DECRETO),
    ThresholdSpec("O2", "actuar", "below", 19.0, "%vol", _DECRETO),
    ThresholdSpec("O2", "evacuar", "below", 17.0, "%vol", _DECRETO),
)

PHYSICAL_MAX: dict[str, float] = {
    "CH4": 5.0,
    "CO": 2000.0,
    "H2S": 200.0,
    "NO2": 100.0,
    "O2": 25.0,
    "CO2": 50_000.0,
}

# |ΔC/Δt| máximo plausible por minuto (unidad canónica).
MAX_RATE_PER_MIN: dict[str, float] = {
    "CH4": 1.0,
    "CO": 200.0,
    "H2S": 20.0,
    "NO2": 20.0,
    "O2": 5.0,
    "CO2": 5_000.0,
}

PRIORITY_GASES: tuple[str, ...] = ("CH4", "CO", "H2S")


def levels_for_gas(gas_code: str) -> list[ThresholdSpec]:
    return [t for t in THRESHOLD_SEED if t.gas_code == gas_code]


def seed_as_records() -> list[dict[str, object]]:
    return [
        {
            "gas_code": t.gas_code,
            "level": t.level,
            "direction": t.direction,
            "value": t.value,
            "unit": t.unit,
            "source_reference": t.source_reference,
            "verified": t.verified,
        }
        for t in THRESHOLD_SEED
    ]


def is_violation(value: float, spec: ThresholdSpec) -> bool:
    if spec.direction == "below":
        return value <= spec.value
    return value >= spec.value
