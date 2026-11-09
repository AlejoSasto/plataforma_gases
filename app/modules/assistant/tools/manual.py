"""Búsqueda en el manual, sin salir de la plataforma."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.manual_index import search
from app.modules.assistant.tools.common import envelope, is_historic, period_for
from app.modules.assistant.tools.params import BuscarManual
from app.modules.users.models import User
from app.shared.access import canonical_role


def run(db: Session, user: User, params: BuscarManual, ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    role = canonical_role(next(iter(user.role_names), "operador"))
    hits = search(params.pregunta, role=role, limit=3)
    window = period_for(db, user, None, None)
    data_until = None
    historic = False
    if not isinstance(window, dict):
        data_until = window[4]
        historic = is_historic(window[2], data_until, None)
    return envelope(
        data_until=data_until,
        historic=historic,
        clamped=False,
        payload={"fragmentos": hits, "n": len(hits)},
    )
