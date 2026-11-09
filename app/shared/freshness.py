"""Etiqueta de la barra: datos al día o hasta la última lectura real."""

from __future__ import annotations

from datetime import datetime, timezone


def data_as_of_label() -> str:
    try:
        from sqlalchemy import func

        from app.core.database import SessionLocal
        from app.modules.sensors_ingestion.models import GasReading
        from app.shared.formatting import format_datetime_short
    except Exception:
        return "Sin lecturas todavía"
    db = SessionLocal()
    try:
        latest = db.query(func.max(GasReading.tiempo_inicio)).scalar()
    except Exception:
        return "Sin lecturas todavía"
    finally:
        db.close()
    if latest is None:
        return "Sin lecturas todavía"
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - latest
    if age.total_seconds() <= 2 * 3600:
        return "Datos al día"
    return f"Datos hasta el {format_datetime_short(latest)}"
