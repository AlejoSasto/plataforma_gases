"""Cobertura y calidad de los datos."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.scope import visible_sensor_ids
from app.modules.assistant.tools.common import envelope, is_historic
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User


def run(db: Session, user: User, params: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    del params, ctx
    ids = visible_sensor_ids(db, user)
    summary = readings.coverage(db, user, ids)
    summary.pop("usuario", None)
    g1 = summary.get("parametros_g1")
    if isinstance(g1, dict):
        summary["parametros_g1"] = {
            "pasos": g1.get("lookback_steps") or g1.get("steps"),
            "horizontes_min": g1.get("horizons") or g1.get("horizontes"),
        }
    data_until = summary.get("hasta")
    return envelope(
        data_until=data_until,
        historic=is_historic(None, data_until, None),
        clamped=False,
        payload=summary,
    )
