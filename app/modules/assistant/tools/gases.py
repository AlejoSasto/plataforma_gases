"""Series y estadísticas de gases."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.tools.common import envelope, equipo_ids, is_historic, period_for
from app.modules.assistant.tools.params import EstadisticasGas, SerieGas
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User
from app.shared.gas_catalog import canonicalize_gas_type


def _check_gas(db: Session, gas: str) -> dict[str, str] | None:
    code = canonicalize_gas_type(gas)
    if code == "UNKNOWN" or code not in readings.known_gases(db):
        return {"error": "No reconozco ese gas. Usa uno del catálogo de la mina."}
    return None


def serie(db: Session, user: User, params: SerieGas, ctx: dict[str, Any]) -> dict[str, Any]:
    bad = _check_gas(db, params.gas)
    if bad:
        return bad
    chosen = equipo_ids(db, user, params.equipo)
    if isinstance(chosen, dict):
        return chosen
    window = period_for(db, user, params.inicio(), params.fin(), chosen)
    if isinstance(window, dict):
        return window
    ids, start, end, clamped, data_until = window
    summary = readings.series_summary(
        db,
        sensor_ids=ids,
        gas=params.gas,
        start=start,
        end=end,
        aggregation=params.agregacion,
        metric=params.metrica,
    )
    if summary.get("error"):
        return summary
    points = summary.pop("points", [])
    ref = f"s_{len(ctx.get('series', {})) + 1}"
    ctx.setdefault("series", {})[ref] = points
    summary["series_ref"] = ref
    summary["puntos_guardados"] = len(points)
    note = summary.get("note")
    if summary.get("n") == 0:
        note = (
            f"No hay lecturas entre {start.date().isoformat()} y {end.date().isoformat()}. "
            f"Los datos llegan hasta {data_until}."
        )
    return envelope(
        data_until=data_until,
        historic=is_historic(end, data_until, None),
        clamped=clamped,
        payload={
            "desde": start.date().isoformat(),
            "hasta": end.date().isoformat(),
            "nota": note,
            **summary,
        },
    )


def estadisticas(db: Session, user: User, params: EstadisticasGas, ctx: dict[str, Any]) -> dict[str, Any]:
    del ctx
    bad = _check_gas(db, params.gas)
    if bad:
        return bad
    window = period_for(db, user, params.inicio(), params.fin())
    if isinstance(window, dict):
        return window
    ids, start, end, clamped, data_until = window
    summary = readings.grouped_stats(
        db,
        sensor_ids=ids,
        gas=params.gas,
        start=start,
        end=end,
        agrupar_por=params.agrupar_por,
    )
    if summary.get("error"):
        return summary
    return envelope(
        data_until=data_until,
        historic=is_historic(end, data_until, None),
        clamped=clamped,
        payload={"desde": start.date().isoformat(), "hasta": end.date().isoformat(), **summary},
    )
