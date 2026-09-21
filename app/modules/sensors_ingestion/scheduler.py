"""Job APScheduler para procesar data/inbox."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.sensors_ingestion import service as ingestion_service

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _inbox_dirs() -> tuple[Path, Path, Path]:
    root = Path(settings.etl_inbox_dir)
    processed = root / "processed"
    failed = root / "failed"
    root.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    failed.mkdir(parents=True, exist_ok=True)
    return root, processed, failed


def process_inbox_once() -> int:
    """Procesa archivos .xlsx pendientes en inbox. Retorna cantidad procesada."""
    root, processed_dir, failed_dir = _inbox_dirs()
    files = sorted(
        [
            p
            for p in root.iterdir()
            if p.is_file() and p.suffix.lower() in {".xlsx", ".xls"}
        ]
    )
    if not files:
        return 0

    count = 0
    db = SessionLocal()
    try:
        for path in files:
            try:
                run = ingestion_service.ingest_excel_paths(db, [path], audit=False)
                dest_dir = processed_dir if run.status == "success" else failed_dir
                dest = dest_dir / path.name
                if dest.exists():
                    dest = dest_dir / f"{path.stem}_{run.id}{path.suffix}"
                shutil.move(str(path), str(dest))
                count += 1
                logger.info(
                    "Inbox ETL file=%s run_id=%s status=%s rows=%s",
                    path.name,
                    run.id,
                    run.status,
                    run.rows_ingested,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Error procesando inbox %s", path.name)
                dest = failed_dir / path.name
                if path.exists():
                    if dest.exists():
                        dest = failed_dir / f"{path.stem}_error{path.suffix}"
                    shutil.move(str(path), str(dest))
    finally:
        db.close()
    return count


def start_inbox_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.etl_inbox_enabled:
        return None
    if _scheduler is not None:
        return _scheduler

    _inbox_dirs()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        process_inbox_once,
        "interval",
        seconds=max(10, settings.etl_inbox_interval_seconds),
        id="etl_inbox",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "APScheduler ETL inbox enabled interval=%ss dir=%s",
        settings.etl_inbox_interval_seconds,
        settings.etl_inbox_dir,
    )
    return scheduler


def shutdown_inbox_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
