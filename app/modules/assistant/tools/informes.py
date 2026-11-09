"""Informes del asistente. Los genera el módulo de reportes, no el modelo."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.tools.common import equipo_ids, period_for
from app.modules.assistant.tools.params import GenerarInforme
from app.modules.reports import service as reports
from app.modules.users.models import User


def run(db: Session, user: User, params: GenerarInforme, ctx: dict[str, Any]) -> dict[str, Any]:
    if not params.desde or not params.hasta:
        return {"error": "Para el informe necesito la fecha inicial y la final, como AAAA-MM-DD."}
    chosen = equipo_ids(db, user, params.equipo)
    if isinstance(chosen, dict):
        return chosen
    window = period_for(db, user, params.inicio(), params.fin(), chosen)
    if isinstance(window, dict):
        return window
    ids, start, end, clamped, data_until = window
    created = reports.create_assistant_report(
        db,
        user,
        kind=params.tipo,
        start=start,
        end=end,
        gas=params.gas,
        sensor_ids=ids,
        formato=params.formato,
        data_until=data_until,
        historic=True,
    )
    ctx.setdefault("reports", []).append(created)
    created["clamped"] = clamped
    created["historic"] = True
    created["data_until"] = data_until
    return created
