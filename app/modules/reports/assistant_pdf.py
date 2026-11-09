"""Informes del asistente en PDF. Los dibuja ReportLab con los mismos agregados que la pantalla.

No usamos ECharts en el servidor: el gráfico del PDF es una tabla y una polilínea
con los puntos que también publica `/api/asistente/graficos`. Así el PDF y la pantalla
salen de la misma lista de números.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Drawing, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.modules.alerts import service as alerts
from app.modules.sensors_ingestion import query as readings
from app.modules.users.models import User
from app.shared.present import reliability_snapshot

INK = colors.HexColor("#1A1E24")
ACCENT = colors.HexColor("#1E3A5F")
MUTED = colors.HexColor("#5C6770")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("AsistTitle", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16, textColor=ACCENT),
        "body": ParagraphStyle("AsistBody", parent=base["Normal"], fontName="Helvetica", fontSize=10, textColor=INK, leading=14),
        "foot": ParagraphStyle("AsistFoot", parent=base["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED),
    }


def _line(points: list[dict[str, Any]]) -> Drawing | None:
    values = [point.get("v") for point in points if isinstance(point.get("v"), (int, float))]
    if len(values) < 2:
        return None
    width, height = 460, 120
    low, high = min(values), max(values)
    span = high - low or 1
    coords = []
    for index, value in enumerate(values[:80]):
        x = 10 + (width - 20) * index / max(len(values[:80]) - 1, 1)
        y = 10 + (height - 20) * (float(value) - low) / span
        coords.extend([x, y])
    drawing = Drawing(width, height)
    drawing.add(PolyLine(coords, strokeColor=ACCENT, strokeWidth=1.4))
    drawing.add(String(10, 2, "Misma serie que la pantalla", fontSize=8, fillColor=MUTED))
    return drawing


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
    styles = _styles()
    origin = "histórico" if historic else "en vivo"
    who = user.full_name or "Usuario"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer = (
        f"Periodo {start.date().isoformat()} a {end.date().isoformat()}. "
        f"Datos hasta {data_until or 'sin marca'}. "
        f"Origen: {origin}. Generado {generated} por {who}."
    )
    story: list[Any] = [Paragraph(_title(kind, gas), styles["title"]), Spacer(1, 0.4 * cm)]
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
            limit=50,
        )
        story.append(Paragraph(f"Avisos en el periodo: {len(rows)}.", styles["body"]))
        data = [["Fecha", "Equipo", "Nivel", "Resultado"]]
        for row in rows:
            data.append([str(row.get("fecha") or "")[:16], row.get("equipo") or "", row.get("nivel") or "", row.get("resultado") or ""])
        story.append(Spacer(1, 0.3 * cm))
        story.append(_table(data or [["Sin avisos"]]))
    elif kind == "resumen_gerencia":
        snap = reliability_snapshot(db)
        story.append(Paragraph(snap.get("recall_phrase") or "", styles["body"]))
        story.append(Paragraph(snap.get("lead_phrase") or "", styles["body"]))
        story.append(Paragraph(snap.get("fa_phrase") or "", styles["body"]))
        story.append(Paragraph(f"Casos evaluados: {snap.get('total') or 0}.", styles["body"]))
    elif kind == "confiabilidad":
        snap = reliability_snapshot(db)
        story.append(Paragraph(snap.get("recall_phrase") or "Sin cifras todavía.", styles["body"]))
        story.append(Paragraph(f"Tamaño de la muestra: {snap.get('total') or 0}.", styles["body"]))
        story.append(Paragraph("Estas cifras salen de los avisos ya evaluados. No reemplazan el criterio del turno.", styles["body"]))
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
        story.append(
            Paragraph(
                f"{summary.get('gas_label') or gas}: {summary.get('n') or 0} lecturas. "
                f"Mínimo {summary.get('min')}, máximo {summary.get('max')}, promedio {summary.get('avg')}.",
                styles["body"],
            )
        )
        drawing = _line(series_points)
        if drawing is not None:
            story.append(Spacer(1, 0.3 * cm))
            story.append(drawing)
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(footer, styles["foot"]))

    def _on_page(canvas, _doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(1.5 * cm, 1.1 * cm, footer[:180])
        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
        title=_title(kind, gas),
        pageCompression=0,
    )
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    meta = {"points": series_points, "footer": footer, "kind": kind}
    return buffer.getvalue(), meta


def _title(kind: str, gas: str | None) -> str:
    names = {
        "avisos_periodo": "Avisos del periodo",
        "resumen_gerencia": "Resumen para gerencia",
        "confiabilidad": "Confiabilidad",
        "comportamiento_gas": f"Comportamiento de {gas or 'gas'}",
    }
    return names.get(kind, "Informe")


def _table(data: list[list[Any]]) -> Table:
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7E1D6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C9C1B4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table
