"""Conversión a unidad canónica por gas (Plan 15 F2 E3)."""

from __future__ import annotations

import re
from typing import Optional

# LIE metano: 5,0 % vol (alternativa IEC 60079-20-1: 4,4). Queda en configuración.
CH4_LEL_PERCENT_VOL = 5.0

_CANONICAL = {
    "CH4": "%vol",
    "CO": "ppm",
    "H2S": "ppm",
    "NO2": "ppm",
    "O2": "%vol",
    "CO2": "ppm",
}


class CanonicalUnitError(ValueError):
    """Unidad no mapeable a la canónica del gas."""


def canonical_unit(gas_code: str) -> str:
    return _CANONICAL.get(gas_code, "")


def _norm_unit(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    text = str(raw).strip().lower()
    text = text.replace("% vol", "%vol").replace("%vol.", "%vol")
    text = re.sub(r"\s+", "", text)
    return text


def to_canonical(
    value: float,
    *,
    gas_code: str,
    unit: Optional[str],
    lel_percent_vol: float = CH4_LEL_PERCENT_VOL,
) -> tuple[float, str]:
    """Devuelve (valor_canónico, unidad_canónica)."""
    target = canonical_unit(gas_code)
    if not target:
        raise CanonicalUnitError(f"gas sin unidad canónica: {gas_code}")
    u = _norm_unit(unit)
    if not u:
        return float(value), target

    if gas_code == "CH4":
        if u in {"%vol", "%v/v", "%"}:
            return float(value), "%vol"
        if u in {"%lel", "lel", "%lie"}:
            return float(value) * (lel_percent_vol / 100.0), "%vol"
        raise CanonicalUnitError(f"unidad CH4 no mapeable: {unit}")

    if gas_code == "CO2":
        if u in {"ppm"}:
            return float(value), "ppm"
        if u in {"%vol", "%v/v", "%"}:
            return float(value) * 10_000.0, "ppm"
        raise CanonicalUnitError(f"unidad CO2 no mapeable: {unit}")

    if gas_code in {"CO", "H2S", "NO2"}:
        if u in {"ppm"}:
            return float(value), "ppm"
        raise CanonicalUnitError(f"unidad {gas_code} no mapeable: {unit}")

    if gas_code == "O2":
        if u in {"%vol", "%v/v", "%"}:
            return float(value), "%vol"
        raise CanonicalUnitError(f"unidad O2 no mapeable: {unit}")

    return float(value), target
