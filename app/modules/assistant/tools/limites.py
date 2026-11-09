"""Límites normativos."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.tools.common import envelope, is_historic, period_for
from app.modules.assistant.tools.params import Limites
from app.modules.catalog import service as catalog
from app.modules.users.models import User


def run(db: Session, user: User, params: Limites, ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    window = period_for(db, user, None, None)
    data_until = None
    historic = False
    if not isinstance(window, dict):
        end = window[2]
        data_until = window[4]
        historic = is_historic(end, data_until, None)
    rows = catalog.limits_for_assistant(db, params.gas)
    if params.gas and not rows:
        return {"error": "No hay límites cargados para ese gas."}
    return envelope(
        data_until=data_until,
        historic=historic,
        clamped=False,
        payload={"limites": rows, "n": len(rows)},
    )
