"""Umbrales del Decreto 1886 que el Plan 25 sí cita con artículo.

Lo que la norma no define no se siembra. verified sigue en false hasta que
una persona confirme el artículo en la pantalla de límites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ThresholdLevel = Literal["vigilar", "actuar", "evacuar"]
Direction = Literal["above", "below"]
Metric = Literal["instantaneo", "twa_8h", "stel_15min"]
SiteKind = Literal["frente", "retorno_tajo", "cualquiera"]
ThresholdKind = Literal["normativo", "politica_empresa"]

METRIC_PLAIN = {
    "instantaneo": "lectura del momento",
    "twa_8h": "promedio de 8 horas",
    "stel_15min": "promedio de 15 minutos",
}


@dataclass(frozen=True)
class ThresholdSpec:
    gas_code: str
    level: ThresholdLevel
    direction: Direction
    value: float
    unit: str
    source_reference: str
    verified: bool = False
    metric: Metric = "instantaneo"
    site_kind: SiteKind = "cualquiera"
    kind: ThresholdKind = "normativo"
    article: str = ""


def _spec(
    gas: str,
    level: ThresholdLevel,
    direction: Direction,
    value: float,
    unit: str,
    article: str,
    *,
    metric: Metric = "instantaneo",
    site_kind: SiteKind = "cualquiera",
) -> ThresholdSpec:
    return ThresholdSpec(
        gas,
        level,
        direction,
        value,
        unit,
        f"Decreto 1886 de 2015, {article}",
        False,
        metric,
        site_kind,
        "normativo",
        article,
    )


THRESHOLD_SEED: tuple[ThresholdSpec, ...] = (
    _spec("CH4", "vigilar", "above", 0.5, "%vol", "Art. 162 (prohíbe voladura) y art. 53 par. 2"),
    _spec(
        "CH4",
        "evacuar",
        "above",
        1.0,
        "%vol",
        "Art. 53 (máximo en frentes) y art. 183 (corte de energía)",
    ),
    _spec("O2", "evacuar", "below", 19.5, "%vol", "Art. 38"),
    _spec("O2", "evacuar", "above", 23.5, "%vol", "Art. 38"),
    _spec("CO", "actuar", "above", 25.0, "ppm", "Art. 39", metric="twa_8h"),
    _spec("H2S", "actuar", "above", 1.0, "ppm", "Art. 39", metric="twa_8h"),
    _spec("H2S", "actuar", "above", 5.0, "ppm", "Art. 39", metric="stel_15min"),
    _spec("CO2", "actuar", "above", 5000.0, "ppm", "Art. 39", metric="twa_8h"),
    _spec("CO2", "actuar", "above", 30000.0, "ppm", "Art. 39", metric="stel_15min"),
    _spec("NO2", "actuar", "above", 0.2, "ppm", "Art. 39", metric="twa_8h"),
)

# Cuando hay sitio: art. 53 distingue frente (1,0 %) y retorno de tajo (1,5 %).
SITE_METHANE: tuple[ThresholdSpec, ...] = (
    _spec("CH4", "evacuar", "above", 1.0, "%vol", "Art. 53", site_kind="frente"),
    _spec("CH4", "evacuar", "above", 1.5, "%vol", "Art. 53", site_kind="retorno_tajo"),
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
            "metric": t.metric,
            "site_kind": t.site_kind,
            "kind": t.kind,
            "article": t.article,
        }
        for t in THRESHOLD_SEED
    ]


def seed_key(spec: ThresholdSpec) -> tuple[str, str, str, str, str]:
    return (spec.gas_code, spec.level, spec.metric, spec.direction, spec.site_kind)


def undefined_levels(defined: set[tuple[str, str]] | None = None) -> list[dict[str, str]]:
    """Niveles que la norma no fija. La interfaz los muestra como no definidos."""
    gases = ("CH4", "CO", "H2S", "O2", "CO2", "NO2")
    levels = ("vigilar", "actuar", "evacuar")
    have = defined
    if have is None:
        have = {(t.gas_code, t.level) for t in THRESHOLD_SEED}
    missing = []
    for gas in gases:
        for level in levels:
            if (gas, level) not in have:
                missing.append(
                    {
                        "gas_code": gas,
                        "level": level,
                        "note": "No definido por la norma. La empresa puede definirlo",
                    }
                )
    return missing


def is_violation(value: float, spec: ThresholdSpec) -> bool:
    if spec.direction == "below":
        return value <= spec.value
    return value >= spec.value
