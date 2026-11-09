"""Verificación de cifras: cada número del texto debe salir de la evidencia del turno."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

_NUMBER = re.compile(r"(?<!\d)\d+(?:[.,]\d+)?(?!\d)")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _num(token: str) -> float:
    return float(token.replace(",", "."))


def _places(token: str) -> int:
    plain = token.replace(",", ".")
    if "." not in plain:
        return 0
    return len(plain.split(".", 1)[1])


def _walk_numbers(value: Any, found: list[float]) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        found.append(float(value))
        return
    if isinstance(value, str):
        for token in _NUMBER.findall(value):
            found.append(_num(token))
        return
    if isinstance(value, dict):
        for item in value.values():
            _walk_numbers(item, found)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _walk_numbers(item, found)


def allowed_numbers(*blobs: Any) -> list[float]:
    found: list[float] = []
    for blob in blobs:
        _walk_numbers(blob, found)
    return found


def number_in_evidence(token: str, allowed: list[float]) -> bool:
    shown = _num(token)
    places = _places(token)
    step = 0.5 * (10 ** (-places))
    for value in allowed:
        if abs(round(value, places) - shown) <= 1e-6 and abs(value - shown) <= step + 1e-9:
            return True
        if abs(value - shown) <= 1e-6:
            return True
    return False


def _blob_text(*blobs: Any) -> str:
    parts: list[str] = []
    for blob in blobs:
        if isinstance(blob, str):
            parts.append(blob)
        else:
            parts.append(json.dumps(blob, ensure_ascii=False, default=str))
    return "\n".join(parts)


def check_reply(reply: str, *blobs: Any) -> str | None:
    """Devuelve el primer token que no está en la evidencia, o None si cuadra."""
    allowed = allowed_numbers(*blobs)
    for token in _NUMBER.findall(reply or ""):
        if not number_in_evidence(token, allowed):
            return token
    text = _blob_text(*blobs)
    for date in _ISO_DATE.findall(reply or ""):
        if date not in text:
            return date
    return None


def data_until_label(value: datetime | str | None) -> str:
    if value is None:
        return ""
    raw = value if isinstance(value, str) else value.isoformat()
    match = _ISO_DATE.search(raw)
    if not match:
        return raw
    year, month, day = match.group(0).split("-")
    months = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )
    return f"{int(day)} de {months[int(month) - 1]} de {year}"
