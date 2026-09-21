"""Motor de reglas de alertas."""

from __future__ import annotations

from app.modules.alerts.recommendations import recommendation_for_gas
from app.modules.predictions.models import Prediction
from app.modules.sensors_ingestion.models import GasReading, Sensor


def has_hard_alarm(reading: GasReading) -> bool:
    alarma = (reading.alarma or "").strip()
    if alarma and alarma.lower() not in {"nan", "none", "null", "0", "false"}:
        return True
    if reading.stel_max is not None and reading.leyendo > reading.stel_max:
        return True
    if reading.twa_max is not None and reading.leyendo > reading.twa_max:
        return True
    return False


def should_create_alert(prediction: Prediction, reading: GasReading) -> bool:
    if prediction.risk_level in {"ALERTA", "CRITICO"}:
        return True
    return has_hard_alarm(reading)


def build_alert_payload(
    prediction: Prediction,
    reading: GasReading,
    sensor: Sensor,
) -> dict:
    level = prediction.risk_level
    if has_hard_alarm(reading) and level in {"NORMAL", "PRECAUCION"}:
        level = "ALERTA"
    gas = sensor.gas_type or sensor.code
    message = (
        f"Riesgo {level} en sensor {sensor.code} ({gas}): "
        f"lectura={reading.leyendo} {reading.unidad or ''}, "
        f"prob={prediction.probability:.2f}"
    ).strip()
    return {
        "level": level,
        "message": message,
        "recommendation": recommendation_for_gas(gas),
    }
