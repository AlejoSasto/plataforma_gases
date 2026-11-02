"""Job de inferencia y cierre de resultados (Plan 17 §9)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert, AlertOutcome
from app.modules.alerts.service import evaluate_and_create_alert
from app.modules.forecasting.models import Forecast, ForecastExplanation, ForecastQuantile
from app.modules.ml_training.models import ModelRegistry
from app.modules.sensors_ingestion.models import GasReading, ReadingGrid, Sensor, ThresholdEvent
from ml_core.forecasting.dataset import to_long
from ml_core.forecasting.problem import ProblemSpec
from ml_core.forecasting.serve import infer_sensor

logger = logging.getLogger(__name__)
PRODUCTION_DIR = Path("storage/models/production")


def _spec_from_settings() -> ProblemSpec:
    return ProblemSpec(lookback=60, horizons=(6, 12, 18), grid_step_minutes=6)


def load_production_forecaster():
    marker = PRODUCTION_DIR / "current.json"
    if not marker.exists():
        return None
    try:
        from ml_core.forecasting.adapters import make_forecaster
        import json

        meta = json.loads(marker.read_text(encoding="utf-8"))
        key = meta.get("model", "persistencia")
        path = PRODUCTION_DIR / key
        cls = make_forecaster(key).__class__
        if path.exists() or path.with_suffix(".json").exists():
            return cls.load(path if path.exists() else path.with_suffix(".json"))
        return make_forecaster(key)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo cargar el modelo en producción")
        return None


def persist_forecast(
    db: Session,
    *,
    sensor_id: int,
    model_id: int,
    issued_at: datetime,
    result,
) -> Forecast:
    existing = (
        db.query(Forecast)
        .filter(
            Forecast.sensor_id == sensor_id,
            Forecast.model_id == model_id,
            Forecast.issued_at == issued_at,
        )
        .first()
    )
    if existing is not None:
        existing.status_level = result.status_level
        existing.exceed_prob = result.exceed_prob
        existing.confidence = result.confidence
        db.add(existing)
        return existing
    fc = Forecast(
        sensor_id=sensor_id,
        model_id=model_id,
        issued_at=issued_at,
        status_level=result.status_level,
        exceed_prob=result.exceed_prob,
        confidence=result.confidence,
    )
    db.add(fc)
    db.flush()
    for q in result.quantiles:
        db.add(
            ForecastQuantile(
                forecast_id=fc.id,
                horizon_min=q["horizon_min"],
                q10=q.get("q10"),
                q50=q.get("q50"),
                q90=q.get("q90"),
                q95=q.get("q95"),
            )
        )
    db.add(
        ForecastExplanation(
            forecast_id=fc.id,
            method="heuristic_window",
            factors=result.factors,
            plain_text=result.plain_text,
        )
    )
    return fc


def _context_for_sensor(db: Session, sensor: Sensor, spec: ProblemSpec) -> pd.DataFrame:
    grid = (
        db.query(ReadingGrid)
        .filter(ReadingGrid.sensor_id == sensor.id)
        .order_by(ReadingGrid.ts.desc())
        .limit(spec.lookback)
        .all()
    )
    if grid:
        df = pd.DataFrame(
            {
                "sensor_code": [sensor.code] * len(grid),
                "ts": [g.ts for g in grid],
                "value": [g.value for g in grid],
                "gas": [sensor.gas_type] * len(grid),
            }
        )
        return to_long(df)
    readings = (
        db.query(GasReading)
        .filter(GasReading.sensor_id == sensor.id)
        .order_by(GasReading.tiempo_inicio.desc())
        .limit(spec.lookback)
        .all()
    )
    df = pd.DataFrame(
        {
            "sensor_code": [sensor.code] * len(readings),
            "ts": [r.tiempo_inicio for r in readings],
            "value": [r.value_canonical if r.value_canonical is not None else r.leyendo for r in readings],
            "gas": [sensor.gas_type] * len(readings),
        }
    )
    return to_long(df)


def run_cycle(db: Session, *, limit: int = 200) -> dict[str, int]:
    spec = _spec_from_settings()
    model = load_production_forecaster()
    production = (
        db.query(ModelRegistry).filter(ModelRegistry.status == "production").first()
    )
    sensors = db.query(Sensor).filter(Sensor.is_active.is_(True)).limit(limit).all()
    n_fc, n_alert = 0, 0
    for sensor in sensors:
        ctx = _context_for_sensor(db, sensor, spec)
        last = (
            db.query(GasReading)
            .filter(GasReading.sensor_id == sensor.id)
            .order_by(GasReading.tiempo_inicio.desc())
            .first()
        )
        last_value = None if last is None else float(last.leyendo)
        result = infer_sensor(
            ctx if not ctx.empty else pd.DataFrame({"unique_id": [sensor.code], "ds": [datetime.now(timezone.utc)], "y": [last_value or 0.0]}),
            spec,
            gas=sensor.gas_type or "CH4",
            model=model,
            last_value=last_value,
        )
        if production is not None and result.quantiles:
            issued = datetime.now(timezone.utc).replace(second=0, microsecond=0)
            persist_forecast(db, sensor_id=sensor.id, model_id=production.id, issued_at=issued, result=result)
            n_fc += 1
        if last is not None and (result.kind == "confirmado" or result.status_level in {"vigilar", "actuar", "evacuar"}):
            fc = None
            if production is not None:
                fc = (
                    db.query(Forecast)
                    .filter(Forecast.sensor_id == sensor.id)
                    .order_by(Forecast.issued_at.desc())
                    .first()
                )
            alert = evaluate_and_create_alert(db, last, forecast=fc)
            if alert is not None:
                n_alert += 1
    db.commit()
    return {"forecasts": n_fc, "alerts": n_alert, "sensors": len(sensors), "has_model": int(model is not None)}


def close_alert_outcomes(db: Session, *, k_max_min: int = 18, tolerance_min: int = 12) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=k_max_min + tolerance_min)
    pending = (
        db.query(Alert)
        .outerjoin(AlertOutcome, AlertOutcome.alert_id == Alert.id)
        .filter(AlertOutcome.alert_id.is_(None))
        .filter(Alert.created_at <= cutoff)
        .all()
    )
    n = 0
    for alert in pending:
        event = (
            db.query(ThresholdEvent)
            .filter(
                ThresholdEvent.sensor_id == alert.sensor_id,
                ThresholdEvent.started_at >= alert.created_at,
                ThresholdEvent.started_at <= alert.created_at + timedelta(minutes=k_max_min + tolerance_min),
            )
            .order_by(ThresholdEvent.started_at.asc())
            .first()
        )
        outcome = "acertado" if event is not None else "falsa_alarma"
        lead = None
        if event is not None:
            lead = (event.started_at - alert.created_at).total_seconds() / 60.0
        db.add(
            AlertOutcome(
                alert_id=alert.id,
                outcome=outcome,
                event_id=event.id if event is not None else None,
                lead_minutes=lead,
                evaluated_at=datetime.now(timezone.utc),
            )
        )
        n += 1
    db.commit()
    return n
