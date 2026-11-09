"""Avisos: búsqueda y detalle, vía el servicio de alertas."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.alerts import service as alerts
from app.modules.assistant.scope import visible_sensor_ids
from app.modules.assistant.tools.common import envelope, equipo_ids, is_historic, period_for
from app.modules.assistant.tools.params import BuscarAvisos, DetalleAviso
from app.modules.sensors_ingestion.models import Sensor
from app.modules.users.models import User
from app.shared.access import canonical_role, scoped_site_ids


def buscar(db: Session, user: User, params: BuscarAvisos, ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    chosen = equipo_ids(db, user, params.equipo)
    if isinstance(chosen, dict):
        return chosen
    window = period_for(db, user, params.inicio(), params.fin(), chosen)
    if isinstance(window, dict):
        return window
    ids, start, end, clamped, data_until = window
    rows = alerts.search_for_assistant(
        db,
        sensor_ids=ids,
        start=start,
        end=end,
        gas=params.gas,
        nivel=params.nivel,
        origin=params.origen,
        status=params.estado,
        limit=params.limite,
    )
    anticipados = sum(1 for row in rows if row["tipo"] == "anticipado")
    historic = is_historic(end, data_until, params.origen) or any(
        row.get("origen") == "historico" for row in rows
    )
    return envelope(
        data_until=data_until,
        historic=historic,
        clamped=clamped,
        payload={
            "desde": start.date().isoformat(),
            "hasta": end.date().isoformat(),
            "avisos": rows,
            "n": len(rows),
            "anticipados": anticipados,
            "confirmados": len(rows) - anticipados,
        },
    )


def detalle(db: Session, user: User, params: DetalleAviso, ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    ids = set(visible_sensor_ids(db, user))
    alert = alerts.get_alert(db, params.id)
    if alert is None or alert.sensor_id not in ids:
        hidden = alerts.get_alert(db, params.id)
        if hidden is not None:
            sensor = db.get(Sensor, hidden.sensor_id)
            scope = scoped_site_ids(db, user)
            if sensor is not None and scope is not None and sensor.site_id not in scope:
                return {"error": "Ese aviso no está en tu alcance."}
        return {"error": "No encuentro ese aviso."}
    role = canonical_role(next(iter(user.role_names), ""))
    include_lineage = role in {"analista", "auditor", "admin"}
    payload = alerts.detail_for_assistant(db, params.id, include_lineage=include_lineage)
    if payload is None:
        return {"error": "No encuentro ese aviso."}
    data_until = payload.get("lectura_en") or payload.get("fecha")
    return envelope(
        data_until=data_until,
        historic=payload.get("origen") == "historico" or is_historic(None, data_until, payload.get("origen")),
        clamped=False,
        payload=payload,
    )
