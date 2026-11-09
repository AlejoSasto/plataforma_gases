"""Informes del asistente en PDF, con el mismo tema que la pantalla de informes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.alerts import service as alerts
from app.modules.catalog.service import limits_for_assistant
from app.modules.reports import generator as reports
from app.modules.reports import pdf_theme as theme
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User
from app.shared import copy
from app.shared.gas_catalog import gas_info
from app.shared.present import reliability_snapshot


def build_pdf(
    db: Session,
    user: User,
    *,
    kind: str,
    start: datetime,
    end: datetime,
    gas: str | None,
    sensor_ids: list[int],
    data_until: str | None,
    historic: bool,
) -> tuple[bytes, dict[str, Any]]:
    who = user.full_name or "Usuario"
    origin = "histórico" if historic else "en vivo"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer = (
        f"Periodo {start.date().isoformat()} a {end.date().isoformat()}. "
        f"Datos hasta {data_until or 'sin marca'}. "
        f"Origen: {origin}. Generado {generated} por {who}."
    )
    series_points: list[dict[str, Any]] = []
    if kind == "avisos_periodo":
        rows = alerts.search_for_assistant(
            db,
            sensor_ids=sensor_ids,
            start=start,
            end=end,
            gas=gas,
            nivel=None,
            origin=None,
            status=None,
            limit=200,
        )
        story = reports._story_avisos(
            [
                {
                    "level": row.get("nivel"),
                    "site": row.get("equipo") or "Sin equipo",
                    "sensor": row.get("gas") or "",
                    "status": row.get("estado"),
                    "when": str(row.get("fecha") or "")[:16].replace("T", " "),
                    "hours": None,
                }
                for row in rows
            ],
            start,
            end,
            zone_heading=copy.PDF_BY_EQUIPO,
        )
        title = copy.PDF_AVISOS_TITLE
    elif kind == "resumen_gerencia":
        snap = reliability_snapshot(db)
        story = [
            theme.paragraph(copy.PDF_GERENCIA_TITLE, "title"),
            theme.paragraph(
                copy.PDF_GERENCIA_LEAD.format(
                    inicio=start.strftime("%d/%m/%Y"),
                    fin=end.strftime("%d/%m/%Y"),
                )
            ),
            theme.paragraph(snap.get("recall_phrase") or ""),
            theme.paragraph(snap.get("lead_phrase") or ""),
            theme.paragraph(snap.get("fa_phrase") or ""),
            theme.paragraph(f"{copy.PDF_SAMPLE}: {snap.get('total') or 0}."),
            theme.paragraph(copy.PDF_BY_LEVEL, "h2"),
        ]
        pairs = [
            (copy.PDF_ON_TIME, int(snap.get("timely") or 0)),
            (copy.PDF_MISSED, int(snap.get("missed") or 0)),
            (copy.PDF_UNNECESSARY, int(snap.get("unnecessary") or 0)),
        ]
        chart = theme.bars(
            pairs,
            fills=[theme.STATUS_COLOR["normal"], theme.STATUS_COLOR["evacuar"], theme.STATUS_COLOR["vigilar"]],
            unit="Avisos",
        )
        if chart is not None:
            story.append(chart)
        title = copy.PDF_GERENCIA_TITLE
    elif kind == "confiabilidad":
        snap = reliability_snapshot(db)
        story = [
            theme.paragraph(copy.PDF_CONFIABILIDAD_TITLE, "title"),
            theme.paragraph(copy.PDF_CONFIABILIDAD_LEAD),
            theme.paragraph(snap.get("recall_phrase") or "Sin cifras todavía."),
            theme.paragraph(f"{copy.PDF_SAMPLE}: {snap.get('total') or 0}."),
            theme.paragraph(copy.PDF_BY_LEVEL, "h2"),
        ]
        pairs = [
            (copy.PDF_ON_TIME, int(snap.get("timely") or 0)),
            (copy.PDF_MISSED, int(snap.get("missed") or 0)),
            (copy.PDF_UNNECESSARY, int(snap.get("unnecessary") or 0)),
        ]
        chart = theme.bars(
            pairs,
            fills=[theme.STATUS_COLOR["normal"], theme.STATUS_COLOR["evacuar"], theme.STATUS_COLOR["vigilar"]],
            unit="Avisos",
        )
        if chart is not None:
            story.append(chart)
        title = copy.PDF_CONFIABILIDAD_TITLE
    else:
        summary = readings.series_summary(
            db,
            sensor_ids=sensor_ids,
            gas=gas or "CH4",
            start=start,
            end=end,
            aggregation="dia",
            metric="valor",
        )
        series_points = list(summary.get("points") or [])
        info = gas_info(gas or summary.get("gas") or "CH4")
        label = summary.get("gas_label") or info.label
        title = copy.PDF_GAS_TITLE.format(gas=theme.plain(label))
        story = [
            theme.paragraph(title, "title"),
            theme.paragraph(
                f"{theme.plain(label)}: {summary.get('n') or 0} lecturas. "
                f"Mínimo {summary.get('min')}, máximo {summary.get('max')}, promedio {summary.get('avg')}."
            ),
        ]
        drawing = theme.series_chart(
            series_points,
            unit=info.unit_default,
            thresholds=_thresholds(db, gas or summary.get("gas")),
            caption=copy.PDF_SERIES,
        )
        if drawing is not None:
            story.append(theme.spacer(6))
            story.append(drawing)
        elif summary.get("note"):
            story.append(theme.paragraph(summary["note"], "muted"))
    blob = theme.render(story, title=title, footer=footer)
    return blob, {"points": series_points, "footer": footer, "kind": kind}


def _thresholds(db: Session, gas: str | None) -> list[tuple[str, float]]:
    picked: dict[str, float] = {}
    for item in limits_for_assistant(db, gas):
        if item.get("metrica") != "lectura del momento":
            continue
        nivel = str(item.get("nivel") or "")
        if nivel in {copy.status_word("vigilar"), copy.status_word("actuar")} and nivel not in picked:
            picked[nivel] = float(item["valor"])
    return list(picked.items())
