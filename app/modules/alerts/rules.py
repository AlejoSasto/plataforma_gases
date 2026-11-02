"""Motor de reglas de alertas."""

from __future__ import annotations

from app.modules.alerts.recommendations import recommendation_for_gas
from app.modules.forecasting.models import Forecast
from app.modules.sensors_ingestion.models import GasReading, Sensor

_FORECAST_ALERT_LEVELS = {"vigilar", "actuar", "evacuar", "ALERTA", "CRITICO"}


def has_hard_alarm(reading: GasReading) -> bool:
    alarma = (reading.alarma or "").strip()
    if alarma and alarma.lower() not in {"nan", "none", "null", "0", "false"}:
        return True
    if reading.stel_max is not None and reading.leyendo > reading.stel_max:
        return True
    if reading.twa_max is not None and reading.leyendo > reading.twa_max:
        return True
    return False


def should_create_alert(reading: GasReading, forecast: Forecast | None = None) -> bool:
    if forecast is not None and forecast.status_level in _FORECAST_ALERT_LEVELS:
        return True
    return has_hard_alarm(reading)


def build_alert_payload(
    reading: GasReading,
    sensor: Sensor,
    forecast: Forecast | None = None,
) -> dict:
    if has_hard_alarm(reading):
        level = "CRITICO" if (forecast and forecast.status_level == "evacuar") else "ALERTA"
        kind = "confirmado"
    elif forecast is not None:
        level = forecast.status_level.upper() if forecast.status_level else "ALERTA"
        kind = "anticipado"
    else:
        level = "ALERTA"
        kind = "confirmado"
    gas = sensor.gas_type or sensor.code
    message = (
        f"Riesgo {level} en sensor {sensor.code} ({gas}): "
        f"lectura={reading.leyendo} {reading.unidad or ''}"
    ).strip()
    rec = recommendation_for_gas(gas)
    return {
        "level": level,
        "kind": kind,
        "message": message,
        "recommendation": rec,
        "plain_message": message,
        "plain_recommendation": rec,
    }
