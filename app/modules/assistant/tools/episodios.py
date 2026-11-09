"""Episodios reales de superación."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.tools.common import envelope, is_historic, period_for
from app.modules.assistant.tools.params import Episodios
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User


def run(db: Session, user: User, params: Episodios, ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    window = period_for(db, user, params.inicio(), params.fin())
    if isinstance(window, dict):
        return window
    ids, start, end, clamped, data_until = window
    summary = readings.episodes(
        db,
        sensor_ids=ids,
        gas=params.gas,
        start=start,
        end=end,
        nivel=params.nivel,
    )
    if summary.get("error"):
        return summary
    return envelope(
        data_until=data_until,
        historic=is_historic(end, data_until, None),
        clamped=clamped,
        payload={"desde": start.date().isoformat(), "hasta": end.date().isoformat(), **summary},
    )
