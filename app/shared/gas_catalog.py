"""Catálogo canónico de gases y normalización de sensores/sitios."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GasInfo:
    code: str
    label: str
    unit_default: str
    thesis_priority: bool = False


GAS_CATALOG: dict[str, GasInfo] = {
    "CH4": GasInfo("CH4", "Metano (CH₄)", "%vol", thesis_priority=True),
    "CO": GasInfo("CO", "Monóxido de carbono (CO)", "ppm", thesis_priority=True),
    "H2S": GasInfo("H2S", "Sulfuro de hidrógeno (H₂S)", "ppm", thesis_priority=True),
    "CO2": GasInfo("CO2", "Dióxido de carbono (CO₂)", "%vol"),
    "O2": GasInfo("O2", "Oxígeno (O₂)", "%vol"),
    "NO2": GasInfo("NO2", "Dióxido de nitrógeno (NO₂)", "ppm"),
    "UNKNOWN": GasInfo("UNKNOWN", "Gas no identificado", ""),
}

# Alias (upper, sin espacios extra) → código canónico
_GAS_ALIASES: dict[str, str] = {
    "CH4": "CH4",
    "METANO": "CH4",
    "METHANE": "CH4",
    "LEL(CH4)": "CH4",
    "LEL": "CH4",
    "GAS COMBUSTIBLE": "CH4",
    "COMBUSTIBLE": "CH4",
    "CO": "CO",
    "MONOXIDO DE CARBONO": "CO",
    "MONÓXIDO DE CARBONO": "CO",
    "CARBON MONOXIDE": "CO",
    "H2S": "H2S",
    "SULFURO DE HIDROGENO": "H2S",
    "SULFURO DE HIDRÓGENO": "H2S",
    "HYDROGEN SULFIDE": "H2S",
    "CO2": "CO2",
    "DIOXIDO DE CARBONO": "CO2",
    "DIÓXIDO DE CARBONO": "CO2",
    "O2": "O2",
    "OXIGENO": "O2",
    "OXÍGENO": "O2",
    "NO2": "NO2",
    "DIOXIDO DE NITROGENO": "NO2",
    "UNKNOWN": "UNKNOWN",
    "UNKNOWN_GAS": "UNKNOWN",
}


def _norm_key(raw: str) -> str:
    text = raw.strip().upper()
    text = text.replace("₄", "4").replace("₂", "2")
    text = re.sub(r"\s+", " ", text)
    return text


def canonicalize_gas_type(raw: Optional[str]) -> str:
    """Devuelve código canónico (CH4, CO, H2S, …)."""
    if not raw or not str(raw).strip():
        return "UNKNOWN"
    key = _norm_key(str(raw))
    if key in _GAS_ALIASES:
        return _GAS_ALIASES[key]
    # Extraer patrón LEL(CH4) / CH4 / H2S embebido
    m = re.search(r"\b(CH4|CO2|H2S|NO2|CO|O2)\b", key)
    if m:
        return m.group(1)
    if "METANO" in key or "METHANE" in key or "LEL" in key:
        return "CH4"
    if "HIDROGENO" in key or "HIDRÓGENO" in key or "SULFIDE" in key:
        return "H2S"
    if "MONOXIDO" in key or "MONÓXIDO" in key:
        return "CO"
    return "UNKNOWN"


def gas_info(code_or_raw: Optional[str]) -> GasInfo:
    code = canonicalize_gas_type(code_or_raw)
    return GAS_CATALOG.get(code, GAS_CATALOG["UNKNOWN"])


def display_gas(code_or_raw: Optional[str]) -> str:
    return gas_info(code_or_raw).label


def normalize_sensor_code(raw: Optional[str]) -> str:
    """Limpia prefijos tipo 'Sensor SN:' y acorta el código."""
    if not raw or not str(raw).strip():
        return "SENSOR-DESCONOCIDO"
    text = str(raw).strip()
    text = re.sub(r"(?i)^sensor\s*sn\s*:\s*", "", text)
    text = re.sub(r"(?i)^sensor\s*:\s*", "", text)
    text = text.strip()
    return text or "SENSOR-DESCONOCIDO"


def display_sensor_code(raw: Optional[str]) -> str:
    code = normalize_sensor_code(raw)
    if len(code) > 28:
        return code[:12] + "…" + code[-10:]
    return code


def normalize_site_name(raw: Optional[str]) -> str:
    if not raw or not str(raw).strip():
        return "Sin sitio asignado"
    name = str(raw).strip()
    if name.upper() in {"SIN_SITIO", "SIN SITIO", "UNKNOWN", "N/A", "NA"}:
        return "Sin sitio asignado"
    return name


def thesis_priority_gases() -> list[str]:
    return [g.code for g in GAS_CATALOG.values() if g.thesis_priority]


def apply_db_catalog(rows: list[object]) -> None:
    """Sustituye el catálogo en memoria con filas de `gas_types` (Plan 16)."""
    global GAS_CATALOG
    if not rows:
        return
    updated: dict[str, GasInfo] = dict(GAS_CATALOG)
    for row in rows:
        code = str(getattr(row, "code", "")).upper()
        if not code:
            continue
        unit = str(getattr(row, "canonical_unit", "") or "")
        name = str(getattr(row, "display_name", "") or code)
        priority = int(getattr(row, "priority", 99) or 99)
        updated[code] = GasInfo(
            code=code,
            label=f"{name} ({code})",
            unit_default=unit,
            thesis_priority=priority <= 3,
        )
    GAS_CATALOG = updated
