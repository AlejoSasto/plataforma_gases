"""Job periódico de pronóstico. El modelo llega en el Plan 17; aquí solo arranca el slot."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def process_pending_forecasts(limit: int = 200) -> int:
    from app.core.database import SessionLocal
    from app.modules.forecasting.cycle import close_alert_outcomes, run_cycle

    db = SessionLocal()
    try:
        stats = run_cycle(db, limit=limit)
        close_alert_outcomes(db)
        return int(stats.get("forecasts", 0) + stats.get("alerts", 0))
    except Exception:  # noqa: BLE001
        logger.exception("Fallo el ciclo de pronóstico")
        return 0
    finally:
        db.close()


def start_forecast_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.prediction_job_enabled:
        return None
    if _scheduler is not None:
        return _scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        process_pending_forecasts,
        "interval",
        seconds=max(30, settings.prediction_job_interval_seconds),
        id="forecasts_pending",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler pronósticos enabled")
    return scheduler


def shutdown_forecast_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
