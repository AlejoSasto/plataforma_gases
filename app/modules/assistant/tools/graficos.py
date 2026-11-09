"""Pide un gráfico a partir de una evidencia de este turno."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assistant.charts import new_chart_id, payload_from_evidence
from app.modules.assistant.tools.params import CrearGrafico
from app.modules.users.models import User


def run(db: Session, user: User, params: CrearGrafico, ctx: dict[str, Any]) -> dict[str, Any]:
    del db, user
    evidence = None
    for item in ctx.get("evidence", []):
        if item.get("evidence_id") == params.ref or item.get("series_ref") == params.ref:
            evidence = item
            break
    if evidence is None:
        return {"error": "Esa referencia no es de este turno. Consulta los datos primero."}
    payload = payload_from_evidence(params.tipo, evidence, ctx.get("series") or {}, params.titulo)
    if payload is None:
        return {"error": "No puedo graficar ese tipo con los datos de esta consulta."}
    chart_id = new_chart_id()
    payload["chart_id"] = chart_id
    payload["data_until"] = evidence.get("data_until")
    ctx.setdefault("charts", {})[chart_id] = payload
    return {
        "chart_id": chart_id,
        "tipo": params.tipo,
        "titulo": params.titulo,
        "data_until": evidence.get("data_until"),
        "historic": evidence.get("historic", False),
        "clamped": False,
        "evidence_id": evidence.get("evidence_id"),
    }
