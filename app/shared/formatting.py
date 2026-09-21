"""Formatters de presentación para UI (lecturas, fechas, gases)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from app.shared.gas_catalog import (
    display_gas as _display_gas,
    display_sensor_code as _display_sensor,
    normalize_site_name,
)

Number = Union[int, float]


def format_reading_value(value: Optional[Number], *, decimals: int = 3) -> Optional[str]:
    """Redondea lecturas para evitar ruido de float y desbordes en tarjetas."""
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num != num:  # NaN
        return None
    rounded = round(num, decimals)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")


def format_datetime_short(value: Optional[Union[datetime, str]]) -> Optional[str]:
    """Fecha legible sin milisegundos: dd/mm/aaaa HH:MM."""
    if value is None:
        return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw[:16].replace("T", " ")
    return value.strftime("%d/%m/%Y %H:%M")


def display_gas(code_or_raw: Optional[str]) -> str:
    return _display_gas(code_or_raw)


def display_sensor_code(raw: Optional[str]) -> str:
    return _display_sensor(raw)


def display_site_name(raw: Optional[str]) -> str:
    return normalize_site_name(raw)
