"""Cifras de confiabilidad, tomadas del mismo cálculo que la pantalla."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.tools.common import envelope, is_historic, period_for
from app.modules.assistant.tools.params import Confiabilidad
from app.modules.users.models import User
from app.shared.present import reliability_snapshot


def run(db: Session, user: User, params: Confiabilidad, ctx: dict[str, Any]) -> dict[str, Any]:
    del params, ctx
    window = period_for(db, user, None, None)
    data_until = None
    historic = False
    if not isinstance(window, dict):
        _ids, end, _clamped_end, _clamped, data_until = window[0], window[2], window[2], window[3], window[4]
        historic = is_historic(end, data_until, None)
    snap = reliability_snapshot(db)
    return envelope(
        data_until=data_until,
        historic=historic,
        clamped=False,
        payload={
            "anticipacion": snap.get("recall_phrase"),
            "minutos": snap.get("lead_phrase"),
            "innecesarios": snap.get("fa_phrase"),
            "a_tiempo": snap.get("timely"),
            "omitidos": snap.get("missed"),
            "avisos_innecesarios": snap.get("unnecessary"),
            "casos": snap.get("total"),
            "minutos_promedio": snap.get("lead_avg"),
            "fuente": "Resultados de los avisos ya evaluados en Vigía",
        },
    )
