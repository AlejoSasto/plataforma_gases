"""Job periódico: predicciones pendientes sobre lecturas reales recientes."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.alerts.service import evaluate_and_create_alert
from app.modules.ml_training import repository as ml_repo
from app.modules.predictions.models import Prediction
from app.modules.predictions.service import predict_for_reading
from app.modules.sensors_ingestion.models import GasReading

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def process_pending_predictions(limit: int = 200) -> int:
    db = SessionLocal()
    try:
        registry = ml_repo.get_production_model(db, scope="global")
        if registry is None:
            return 0

        import mlflow

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        model = mlflow.pyfunc.load_model(registry.artifact_uri)
        bundle = (registry, model)

        subq = db.query(Prediction.gas_reading_id)
        readings = (
            db.query(GasReading)
            .filter(
                GasReading.is_synthetic.is_(False),
                ~GasReading.id.in_(subq),
            )
            .order_by(GasReading.id.desc())
            .limit(limit)
            .all()
        )
        count = 0
        for reading in readings:
            try:
                pred = predict_for_reading(db, reading, model_bundle=bundle)
                evaluate_and_create_alert(db, pred, reading)
                count += 1
            except Exception:  # noqa: BLE001
                logger.exception("Fallo predicción reading_id=%s", reading.id)
        db.commit()
        return count
    finally:
        db.close()


def start_prediction_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.prediction_job_enabled:
        return None
    if _scheduler is not None:
        return _scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        process_pending_predictions,
        "interval",
        seconds=max(30, settings.prediction_job_interval_seconds),
        id="predictions_pending",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler predicciones enabled")
    return scheduler


def shutdown_prediction_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
