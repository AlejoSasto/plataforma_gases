"""Factores → frase natural con plantillas fijas (sin LLM)."""

from __future__ import annotations

from typing import Any

from ml_core.forecasting.explain.factors import FACTOR_CODES
from ml_core.forecasting.explain.language import assert_plain

TEMPLATES: dict[str, str] = {
    "tendencia_subida": "El {gas} viene subiendo de forma sostenida en los últimos {n} minutos",
    "nivel_alto": "El nivel actual ya está cerca del límite de {nivel}",
    "subida_brusca": "Hubo un aumento repentino hace {n} minutos",
    "otro_gas": "El {otro_gas} en la misma zona también está subiendo",
    "temperatura": "La temperatura en la zona aumentó",
    "hora_turno": "A esta hora suelen registrarse aumentos en esta zona",
}

CONNECTOR = " Además, "


def narrate(factors: list[dict[str, Any]], *, max_factors: int = 3) -> str:
    if not factors:
        text = "Los sensores muestran un cambio que conviene vigilar en esta zona."
        assert_plain(text)
        return text
    phrases: list[str] = []
    for row in factors[:max_factors]:
        code = str(row.get("factor_code", ""))
        template = TEMPLATES.get(code)
        if template is None:
            continue
        payload = {
            "gas": row.get("gas", "gas"),
            "n": row.get("n", 6),
            "nivel": row.get("nivel", "vigilar"),
            "otro_gas": row.get("otro_gas", "otro gas"),
        }
        phrases.append(template.format(**payload))
    if not phrases:
        text = "Los sensores muestran un cambio que conviene vigilar en esta zona."
    elif len(phrases) == 1:
        text = phrases[0] + "."
    else:
        text = phrases[0] + "." + CONNECTOR + phrases[1][0].lower() + phrases[1][1:]
        if len(phrases) > 2:
            text += " " + phrases[2] + "."
        else:
            text += "."
    assert_plain(text)
    return text


def templates_cover_catalog() -> None:
    missing = [c for c in FACTOR_CODES if c not in TEMPLATES]
    if missing:
        raise AssertionError(f"faltan plantillas para {missing}")
