"""Estado actual por equipo y gas."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.scope import visible_sensor_ids
from app.modules.assistant.tools.common import envelope, is_historic
from app.modules.dashboard import service as dashboard
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User
from app.shared.copy import status_word


def run(db: Session, user: User, params: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    del params, ctx
    ids = set(visible_sensor_ids(db, user))
    cards = [card for card in dashboard.semaforo(db, user=user) if card["sensor_id"] in ids]
    start, end = readings.data_bounds(db, list(ids))
    data_until = end.isoformat() if end else None
    rows = []
    for card in cards[:200]:
        rows.append(
            {
                "equipo": card.get("sensor_code"),
                "gas": card.get("gas_type"),
                "nivel": status_word(card.get("risk_level")),
                "lectura": card.get("last_value"),
                "esperado": card.get("predicted_concentration"),
                "cuando": card.get("last_at"),
            }
        )
    return envelope(
        data_until=data_until,
        historic=is_historic(end, data_until, None),
        clamped=False,
        payload={"equipos": rows, "n": len(rows)},
    )
