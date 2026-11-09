"""Tema compartido de los informes PDF: marca, ejes y tablas."""

from __future__ import annotations

from io import BytesIO
from typing import Any, Sequence
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.shared import copy

INK = colors.HexColor("#1A1E24")
ACCENT = colors.HexColor("#1C5A8E")
MUTED = colors.HexColor("#4A525E")
LINE_COLOR = colors.HexColor("#DCE0E3")
HEADER_BG = colors.HexColor("#E5EEF6")
SOFT = colors.HexColor("#F5F6F6")
EYE = colors.HexColor("#7FB2E5")

STATUS_COLOR = {
    "normal": colors.HexColor("#1F8A5B"),
    "vigilar": colors.HexColor("#B97E00"),
    "actuar": colors.HexColor("#D2581A"),
    "evacuar": colors.HexColor("#C1262E"),
    "sin_datos": colors.HexColor("#7D8590"),
}

_WORD_KEY = {copy.status_word(key): key for key in STATUS_COLOR}
_PLAIN = str.maketrans(
    {
        "₀": "0",
        "₁": "1",
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
        "—": "-",
        "–": "-",
        "→": "-",
        "·": "-",
    }
)

_STATE = {
    "abierta": "Abierto",
    "open": "Abierto",
    "reconocida": "Visto",
    "acknowledged": "Visto",
    "resuelta": "Cerrado",
    "resolved": "Cerrado",
    "pendiente": "Pendiente",
}


def plain(value: object) -> str:
    text = "" if value is None else str(value)
    return text.translate(_PLAIN)


def state_word(value: object) -> str:
    raw = plain(value).strip()
    return _STATE.get(raw.casefold(), raw or "—")


def styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "VigiaTitle",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=INK,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "VigiaH2",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=ACCENT,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "VigiaBody",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=INK,
        ),
        "muted": ParagraphStyle(
            "VigiaMuted",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=MUTED,
        ),
        "kpi": ParagraphStyle(
            "VigiaKpi",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=1,
            textColor=INK,
        ),
        "kpi_label": ParagraphStyle(
            "VigiaKpiLabel",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "VigiaCell",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=INK,
        ),
        "head": ParagraphStyle(
            "VigiaHead",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=ACCENT,
        ),
    }


def paragraph(text: object, kind: str = "body") -> Paragraph:
    return Paragraph(escape(plain(text)), styles()[kind])


def kpis(items: Sequence[tuple[str, str]]) -> Table:
    look = styles()
    width = _content_width() / max(len(items), 1)
    data = [
        [Paragraph(escape(plain(value)), look["kpi"]) for _label, value in items],
        [Paragraph(escape(plain(label)), look["kpi_label"]) for label, _value in items],
    ]
    table = Table(data, colWidths=[width] * len(items))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.4, LINE_COLOR),
                ("LINEAFTER", (0, 0), (-2, -1), 0.3, LINE_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def data_table(rows: Sequence[Sequence[Any]], widths: Sequence[float]) -> Table:
    look = styles()
    painted: list[list[Any]] = []
    for index, row in enumerate(rows):
        kind = "head" if index == 0 else "cell"
        painted.append([cell if _is_flowable(cell) else Paragraph(escape(plain(cell)), look[kind]) for cell in row])
    table = Table(painted, colWidths=list(widths), repeatRows=1)
    commands: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
    ]
    header = [plain(cell) for cell in rows[0]] if rows else []
    if "Nivel" in header:
        col = header.index("Nivel")
        for row_index, row in enumerate(rows[1:], start=1):
            key = _WORD_KEY.get(plain(row[col]))
            if key:
                commands.append(("TEXTCOLOR", (col, row_index), (col, row_index), STATUS_COLOR[key]))
    table.setStyle(TableStyle(commands))
    return table


def bars(
    pairs: Sequence[tuple[str, float]],
    *,
    fills: Sequence[colors.Color] | None = None,
    unit: str = "",
    width: float | None = None,
    height: float = 168,
) -> Drawing | None:
    if not pairs:
        return None
    width = width or _content_width()
    labels = [plain(label)[:18] for label, _value in pairs]
    values = [float(value) for _label, value in pairs]
    drawing = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x = 42
    chart.y = 28
    chart.height = height - 46
    chart.width = width - 56
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = MUTED
    if len(labels) > 4:
        chart.categoryAxis.labels.angle = 25
        chart.categoryAxis.labels.boxAnchor = "e"
        chart.categoryAxis.labels.dy = -6
    peak = max(values) if values else 0
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = peak * 1.25 if peak else 1
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.visibleGrid = 1
    chart.valueAxis.gridStrokeColor = LINE_COLOR
    chart.barWidth = min(22, chart.width / max(len(labels) * 2, 1))
    chart.groupSpacing = 10
    chart.strokeColor = colors.white
    drawing.add(chart)
    palette = list(fills or [ACCENT] * len(labels))
    for index, color in enumerate(palette):
        chart.bars[(0, index)].fillColor = color
    if unit:
        drawing.add(String(42, height - 12, plain(unit), fontName="Helvetica", fontSize=8, fillColor=MUTED))
    return drawing


def series_chart(
    points: Sequence[dict[str, Any]],
    *,
    unit: str = "",
    thresholds: Sequence[tuple[str, float]] | None = None,
    caption: str = "",
    width: float | None = None,
    height: float = 190,
) -> Drawing | None:
    clean = [(plain(point.get("t")), float(point["v"])) for point in points if isinstance(point.get("v"), (int, float))]
    if len(clean) < 2:
        return None
    clean = clean[:80]
    width = width or _content_width()
    values = [value for _label, value in clean]
    low, high = min(values), max(values)
    extra = [value for _name, value in (thresholds or [])]
    if extra:
        low = min(low, min(extra))
        high = max(high, max(extra))
    span = high - low or 1
    y_min = low - span * 0.12
    y_max = high + span * 0.18
    drawing = Drawing(width, height)
    plot = LinePlot()
    plot.x = 46
    plot.y = 34
    plot.height = height - 58
    plot.width = width - 62
    plot.data = [[(index, value) for index, (_label, value) in enumerate(clean)]]
    plot.joinedLines = 1
    plot.lines[0].strokeColor = ACCENT
    plot.lines[0].strokeWidth = 1.6
    plot.lines[0].symbol = makeMarker("FilledCircle")
    plot.lines[0].symbol.size = 3
    plot.lines[0].symbol.fillColor = ACCENT
    plot.xValueAxis.valueMin = 0
    plot.xValueAxis.valueMax = max(len(clean) - 1, 1)
    plot.xValueAxis.labels.fontSize = 0
    plot.xValueAxis.visibleTicks = 0
    plot.yValueAxis.valueMin = y_min
    plot.yValueAxis.valueMax = y_max
    plot.yValueAxis.labels.fontName = "Helvetica"
    plot.yValueAxis.labels.fontSize = 7
    plot.yValueAxis.labels.fillColor = MUTED
    plot.yValueAxis.visibleGrid = 1
    plot.yValueAxis.gridStrokeColor = LINE_COLOR
    drawing.add(plot)

    def y_of(value: float) -> float:
        return plot.y + (value - y_min) / (y_max - y_min) * plot.height

    for name, value in thresholds or []:
        y = y_of(float(value))
        if y < plot.y or y > plot.y + plot.height:
            continue
        key = _WORD_KEY.get(plain(name), "actuar")
        color = STATUS_COLOR.get(key, ACCENT)
        drawing.add(Line(plot.x, y, plot.x + plot.width, y, strokeColor=color, strokeWidth=0.8))
        drawing.add(String(plot.x + 4, y + 2, plain(name)[:16], fontName="Helvetica", fontSize=7, fillColor=color))
    marks = [0, len(clean) // 2, len(clean) - 1]
    seen: set[int] = set()
    for index in marks:
        if index in seen:
            continue
        seen.add(index)
        x = plot.x + plot.width * index / max(len(clean) - 1, 1)
        drawing.add(String(x - 18, 8, clean[index][0][:10], fontName="Helvetica", fontSize=7, fillColor=MUTED))
    title = caption or unit
    if title:
        drawing.add(String(46, height - 12, plain(title), fontName="Helvetica", fontSize=8, fillColor=MUTED))
    return drawing


def render(story: list[Any], *, title: str, footer: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.9 * cm,
        bottomMargin=1.5 * cm,
        title=plain(title),
        author=copy.BRAND,
        pageCompression=0,
    )
    deco = _page(plain(title), plain(footer))
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
    return buffer.getvalue()


def spacer(points: float = 8) -> Spacer:
    return Spacer(1, points)


def _content_width() -> float:
    return A4[0] - 3.2 * cm


def _is_flowable(value: Any) -> bool:
    return hasattr(value, "wrap") and hasattr(value, "draw")


def _page(title: str, footer: str):  # type: ignore[no-untyped-def]
    def draw(canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(INK)
        canvas.rect(0, height - 1.15 * cm, width, 1.15 * cm, fill=1, stroke=0)
        _mark(canvas, 1.15 * cm, height - 0.95 * cm, 0.62 * cm)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(2.0 * cm, height - 0.74 * cm, copy.BRAND)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - 1.4 * cm, height - 0.74 * cm, title[:48])
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.6 * cm, 0.7 * cm, footer[:220])
        canvas.drawRightString(width - 1.6 * cm, 0.7 * cm, f"{doc.page}")
        canvas.restoreState()

    return draw


def _mark(canvas, x: float, y: float, size: float) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setStrokeColor(EYE)
    canvas.setLineWidth(1.3)
    canvas.setLineCap(1)
    canvas.circle(x + size * 0.5, y + size * 0.62, size * 0.28, stroke=1, fill=0)
    canvas.circle(x + size * 0.5, y + size * 0.62, size * 0.16, stroke=1, fill=0)
    canvas.setFillColor(colors.white)
    canvas.circle(x + size * 0.5, y + size * 0.62, size * 0.06, stroke=0, fill=1)
    canvas.setStrokeColor(colors.white)
    canvas.setLineWidth(1.4)
    canvas.line(x + size * 0.5, y + size * 0.42, x + size * 0.5, y + size * 0.08)
    canvas.restoreState()


def status_fills(labels: Sequence[str]) -> list[colors.Color]:
    fills: list[colors.Color] = []
    for label in labels:
        key = _WORD_KEY.get(plain(label))
        fills.append(STATUS_COLOR.get(key, ACCENT) if key else ACCENT)
    return fills
