"""Gráficos del turno. El servidor arma los datos; el modelo solo cita la referencia."""

from __future__ import annotations

from typing import Any
from uuid import uuid4


def new_chart_id() -> str:
    return "c_" + uuid4().hex[:8]


def payload_from_evidence(kind: str, evidence: dict[str, Any], series: dict[str, list], title: str) -> dict[str, Any] | None:
    if kind == "serie":
        ref = evidence.get("series_ref")
        points = series.get(ref) or evidence.get("points") or []
        return {
            "kind": "serie",
            "title": title,
            "measured": [{"t": point["t"], "v": point["v"]} for point in points],
            "empty_message": evidence.get("nota") or "No hay lecturas en este periodo",
        }
    if kind == "estadistica":
        groups = evidence.get("grupos") or []
        return {
            "kind": "estadistica",
            "title": title,
            "categories": [row.get("grupo") for row in groups],
            "values": [row.get("avg") for row in groups],
            "empty_message": "No hay grupos en este periodo",
        }
    if kind == "avisos_por_periodo":
        avisos = evidence.get("avisos") or []
        counts: dict[str, int] = {}
        for row in avisos:
            day = str(row.get("fecha") or "")[:10] or "sin fecha"
            counts[day] = counts.get(day, 0) + 1
        return {
            "kind": "avisos_por_periodo",
            "title": title,
            "categories": list(counts),
            "values": list(counts.values()),
            "empty_message": "No hay avisos en este periodo",
        }
    if kind == "confiabilidad":
        return {
            "kind": "confiabilidad",
            "title": title,
            "items": [
                {"label": "A tiempo", "value": evidence.get("a_tiempo") or 0},
                {"label": "Omitidos", "value": evidence.get("omitidos") or 0},
                {"label": "Innecesarios", "value": evidence.get("avisos_innecesarios") or 0},
            ],
            "empty_message": "Aún no hay cifras de anticipación para graficar",
        }
    return None
