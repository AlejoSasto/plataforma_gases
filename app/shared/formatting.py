"""Formatters de presentación para UI (lecturas, fechas)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

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
