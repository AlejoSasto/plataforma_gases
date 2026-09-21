"""Generadores de reportes PDF (ReportLab) y Excel (openpyxl).

Paleta alineada con theme.css (Plan 07):
  primary #0E9F6E, info #0EA5E9, risk colors.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.modules.alerts import service as alerts_service
from app.modules.alerts.models import Alert
from app.modules.ml_training.repository import get_model, list_models
from app.modules.sensors_ingestion.models import GasReading, Sensor
from app.modules.stakeholders.service import alert_ids_visible_to_user

PRIMARY = colors.HexColor("#0E9F6E")
INFO = colors.HexColor("#0EA5E9")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
HEADER_BG = colors.HexColor("#ECFDF5")
RISK_COLORS = {
    "NORMAL": colors.HexColor("#16A34A"),
    "PRECAUCION": colors.HexColor("#F59E0B"),
    "ALERTA": colors.HexColor("#EA580C"),
    "CRITICO": colors.HexColor("#DC2626"),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitlePG",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=PRIMARY,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2PG",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=TEXT,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "BodyPG",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT,
            leading=12,
        ),
        "muted": ParagraphStyle(
            "MutedPG",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
        ),
    }


def _period_bounds(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    # incluir día end completo
    if end.hour == 0 and end.minute == 0 and end.second == 0:
        end = end.replace(hour=23, minute=59, second=59)
    return start, end


def _query_alerts(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    visible_ids: Optional[set[int]] = None,
) -> list[Alert]:
    start, end = _period_bounds(start, end)
    q = db.query(Alert).filter(Alert.created_at >= start, Alert.created_at <= end)
    if visible_ids is not None:
        if not visible_ids:
            return []
        q = q.filter(Alert.id.in_(visible_ids))
    return q.order_by(Alert.created_at.desc()).all()


def _avg_resolution_hours(alerts: list[Alert]) -> Optional[float]:
    deltas = []
    for a in alerts:
        if a.resolved_at and a.created_at:
            deltas.append((a.resolved_at - a.created_at).total_seconds() / 3600.0)
    if not deltas:
        return None
    return round(sum(deltas) / len(deltas), 2)


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), PRIMARY),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )


def generate_alertas_periodo(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    visible_ids: Optional[set[int]] = None,
) -> bytes:
    styles = _styles()
    alerts = _query_alerts(db, start, end, visible_ids=visible_ids)
    by_level: dict[str, int] = {}
    for a in alerts:
        by_level[a.level] = by_level.get(a.level, 0) + 1
    avg_h = _avg_resolution_hours(alerts)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Reporte de alertas",
    )
    story: list[Any] = []
    story.append(Paragraph("Plataforma Gases — Alertas por periodo", styles["title"]))
    story.append(
        Paragraph(
            f"Periodo: {start.date().isoformat()} → {end.date().isoformat()} · "
            f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["muted"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("Resumen", styles["h2"]))
    summary_rows = [
        ["Total alertas", str(len(alerts))],
        ["Tiempo medio resolución (h)", str(avg_h) if avg_h is not None else "N/D"],
    ]
    for level in ("CRITICO", "ALERTA", "PRECAUCION", "NORMAL"):
        if level in by_level:
            summary_rows.append([f"Nivel {level}", str(by_level[level])])
    t_sum = Table(summary_rows, colWidths=[8 * cm, 4 * cm])
    t_sum.setStyle(_table_style())
    story.append(t_sum)
    story.append(Paragraph("Detalle", styles["h2"]))

    header = ["ID", "Nivel", "Sitio", "Sensor", "Estado", "Fecha", "Mensaje"]
    data = [header]
    for a in alerts[:500]:
        d = alerts_service.alert_to_dict(db, a)
        data.append(
            [
                str(d["id"]),
                d["level"],
                (d.get("site_name") or "—")[:24],
                (d.get("sensor_code") or str(d["sensor_id"]))[:18],
                d["status"],
                d["created_at"].strftime("%Y-%m-%d %H:%M")
                if hasattr(d["created_at"], "strftime")
                else str(d["created_at"])[:16],
                Paragraph((d.get("message") or "")[:120], styles["body"]),
            ]
        )
    if len(data) == 1:
        data.append(["—", "—", "—", "—", "—", "—", "Sin alertas en el periodo"])
    t = Table(
        data,
        colWidths=[1.2 * cm, 2.2 * cm, 3.5 * cm, 3 * cm, 2.2 * cm, 3 * cm, 10 * cm],
    )
    t.setStyle(_table_style())
    story.append(t)
    doc.build(story)
    return buf.getvalue()


def generate_desempeno_modelo(db: Session, model_registry_id: int) -> bytes:
    styles = _styles()
    model = get_model(db, model_registry_id)
    if model is None:
        raise ValueError("Modelo no encontrado")

    others = [
        m
        for m in list_models(db)
        if m.id != model.id and m.scope == model.scope
    ]
    prev = others[0] if others else None

    metrics = model.metrics or {}
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Desempeño modelo {model.name}",
    )
    story: list[Any] = []
    story.append(Paragraph("Plataforma Gases — Desempeño de modelo", styles["title"]))
    story.append(
        Paragraph(
            f"{model.name} v{model.version} · {model.algorithm} · estado {model.status}",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"Entrenado: {model.trained_at.isoformat() if model.trained_at else 'N/D'}",
            styles["muted"],
        )
    )
    story.append(Paragraph("Métricas", styles["h2"]))
    rows = [["Métrica", "Valor"]]
    for key in (
        "precision",
        "recall",
        "f1",
        "false_negative_rate",
        "rmse",
        "mae",
        "lead_time_hit_rate",
        "lead_time_minutes_mean",
        "f1_score",
        "accuracy",
        "roc_auc",
    ):
        if key in metrics and metrics[key] is not None:
            val = metrics[key]
            rows.append(
                [
                    key,
                    f"{val:.4f}" if isinstance(val, float) else str(val),
                ]
            )
    gates = metrics.get("gates") or {}
    if gates:
        story.append(Paragraph("Gates thesis", styles["h2"]))
        grow = [["Gate", "Cumple"]]
        for k, v in gates.items():
            grow.append([k, "Sí" if v else ("N/A" if v is None else "No")])
        gt = Table(grow, colWidths=[8 * cm, 6 * cm])
        gt.setStyle(_table_style())
        story.append(gt)
    if len(rows) == 1:
        for k, v in metrics.items():
            if k in ("gates", "thresholds", "confusion_matrix"):
                continue
            rows.append([str(k), str(v)])
    t = Table(rows, colWidths=[8 * cm, 6 * cm])
    t.setStyle(_table_style())
    story.append(t)

    cm_data = metrics.get("confusion_matrix") or metrics.get("confusion")
    if cm_data:
        story.append(Paragraph("Matriz de confusión", styles["h2"]))
        story.append(Paragraph(str(cm_data), styles["body"]))
    else:
        story.append(
            Paragraph(
                "Matriz de confusión: no persistida en el registro del modelo.",
                styles["muted"],
            )
        )

    story.append(Paragraph("Comparación con modelo anterior", styles["h2"]))
    if prev is None:
        story.append(Paragraph("No hay otro modelo en el mismo scope para comparar.", styles["body"]))
    else:
        prev_m = prev.metrics or {}
        cmp_rows = [["Métrica", "Actual", f"Anterior #{prev.id}"]]
        for key in ("precision", "recall", "f1", "f1_score"):
            a = metrics.get(key)
            b = prev_m.get(key)
            if a is None and b is None:
                continue
            cmp_rows.append(
                [
                    key,
                    f"{a:.4f}" if isinstance(a, float) else str(a or "—"),
                    f"{b:.4f}" if isinstance(b, float) else str(b or "—"),
                ]
            )
        ct = Table(cmp_rows, colWidths=[5 * cm, 5 * cm, 5 * cm])
        ct.setStyle(_table_style())
        story.append(ct)
        story.append(
            Paragraph(
                f"Anterior: {prev.name} v{prev.version} ({prev.algorithm}) · {prev.status}",
                styles["muted"],
            )
        )

    doc.build(story)
    return buf.getvalue()


def generate_resumen_ejecutivo(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    stakeholder_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> bytes:
    """Excel con alertas por sitio, tendencia y recomendaciones."""
    visible: Optional[set[int]] = None
    if user_id is not None:
        visible = alert_ids_visible_to_user(db, user_id)
    alerts = _query_alerts(db, start, end, visible_ids=visible)

    # Si stakeholder_id explícito, filtrar por suscripciones del stakeholder
    if stakeholder_id is not None:
        from app.modules.stakeholders.models import StakeholderSubscription
        from app.modules.stakeholders.service import LEVEL_RANK

        subs = (
            db.query(StakeholderSubscription)
            .filter(StakeholderSubscription.stakeholder_id == stakeholder_id)
            .all()
        )
        if not subs:
            alerts = []
        else:
            filtered = []
            for a in alerts:
                d = alerts_service.alert_to_dict(db, a)
                sensor = db.query(Sensor).filter(Sensor.id == a.sensor_id).first()
                site_id = sensor.site_id if sensor else None
                for sub in subs:
                    if LEVEL_RANK.get(a.level, 0) < LEVEL_RANK.get(sub.min_level, 0):
                        continue
                    if sub.sensor_id and sub.sensor_id != a.sensor_id:
                        continue
                    if sub.site_id and sub.site_id != site_id:
                        continue
                    filtered.append(a)
                    break
            alerts = filtered

    wb = Workbook()
    # Hoja resumen
    ws = wb.active
    ws.title = "Resumen"
    header_fill = PatternFill("solid", fgColor="0E9F6E")
    header_font = Font(bold=True, color="FFFFFF")
    ws["A1"] = "Plataforma Gases — Resumen ejecutivo"
    ws["A1"].font = Font(bold=True, size=14, color="0E9F6E")
    ws["A2"] = f"Periodo: {start.date().isoformat()} → {end.date().isoformat()}"
    ws["A3"] = f"Total alertas: {len(alerts)}"
    avg_h = _avg_resolution_hours(alerts)
    ws["A4"] = f"Tiempo medio resolución (h): {avg_h if avg_h is not None else 'N/D'}"

    by_level: dict[str, int] = {}
    by_site: dict[str, int] = {}
    for a in alerts:
        by_level[a.level] = by_level.get(a.level, 0) + 1
        d = alerts_service.alert_to_dict(db, a)
        site = d.get("site_name") or "N/D"
        by_site[site] = by_site.get(site, 0) + 1

    ws["A6"] = "Alertas por nivel"
    ws["A6"].font = Font(bold=True)
    ws.append([])  # won't work well - use cells
    row = 7
    ws.cell(row, 1, "Nivel")
    ws.cell(row, 2, "Cantidad")
    for c in (1, 2):
        ws.cell(row, c).fill = header_fill
        ws.cell(row, c).font = header_font
    row = 8
    for level, count in sorted(by_level.items(), key=lambda x: -x[1]):
        ws.cell(row, 1, level)
        ws.cell(row, 2, count)
        row += 1

    row += 1
    ws.cell(row, 1, "Alertas por sitio")
    ws.cell(row, 1).font = Font(bold=True)
    row += 1
    ws.cell(row, 1, "Sitio")
    ws.cell(row, 2, "Cantidad")
    for c in (1, 2):
        ws.cell(row, c).fill = header_fill
        ws.cell(row, c).font = header_font
    row += 1
    for site, count in sorted(by_site.items(), key=lambda x: -x[1]):
        ws.cell(row, 1, site)
        ws.cell(row, 2, count)
        row += 1

    # Hoja detalle
    wd = wb.create_sheet("Alertas")
    headers = [
        "ID",
        "Nivel",
        "Sitio",
        "Sensor",
        "Gas",
        "Estado",
        "Fecha",
        "Mensaje",
        "Recomendación",
    ]
    for col, h in enumerate(headers, 1):
        cell = wd.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True)
    for i, a in enumerate(alerts, 2):
        d = alerts_service.alert_to_dict(db, a)
        created = d["created_at"]
        created_s = (
            created.isoformat() if hasattr(created, "isoformat") else str(created)
        )
        wd.cell(i, 1, d["id"])
        wd.cell(i, 2, d["level"])
        wd.cell(i, 3, d.get("site_name") or "")
        wd.cell(i, 4, d.get("sensor_code") or "")
        wd.cell(i, 5, d.get("gas_type") or "")
        wd.cell(i, 6, d["status"])
        wd.cell(i, 7, created_s)
        wd.cell(i, 8, d.get("message") or "")
        wd.cell(i, 9, d.get("recommendation") or "")

    # Tendencia gases (conteo lecturas por gas_type en periodo)
    wt = wb.create_sheet("Tendencia_gases")
    start_b, end_b = _period_bounds(start, end)
    from sqlalchemy import func

    gas_agg = (
        db.query(Sensor.gas_type, func.count(GasReading.id))
        .join(GasReading, GasReading.sensor_id == Sensor.id)
        .filter(GasReading.tiempo_inicio >= start_b, GasReading.tiempo_inicio <= end_b)
        .group_by(Sensor.gas_type)
        .all()
    )
    wt.cell(1, 1, "Gas").fill = header_fill
    wt.cell(1, 1).font = header_font
    wt.cell(1, 2, "Lecturas").fill = header_fill
    wt.cell(1, 2).font = header_font
    for i, (gas, cnt) in enumerate(gas_agg, 2):
        wt.cell(i, 1, gas or "UNKNOWN")
        wt.cell(i, 2, cnt)

    # Recomendaciones acumuladas
    wr = wb.create_sheet("Recomendaciones")
    wr.cell(1, 1, "Recomendación").fill = header_fill
    wr.cell(1, 1).font = header_font
    wr.cell(1, 2, "Veces").fill = header_fill
    wr.cell(1, 2).font = header_font
    rec_counts: dict[str, int] = {}
    for a in alerts:
        rec = (a.recommendation or "").strip() or "(sin recomendación)"
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
    for i, (rec, cnt) in enumerate(sorted(rec_counts.items(), key=lambda x: -x[1]), 2):
        wr.cell(i, 1, rec)
        wr.cell(i, 2, cnt)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_comparativa_modelos(db: Session) -> bytes:
    """Excel con matriz unificada thesis de todos los modelos registrados."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Comparativa"
    header_fill = PatternFill("solid", fgColor="0F766E")
    header_font = Font(color="FFFFFF", bold=True)
    headers = [
        "id",
        "name",
        "algorithm",
        "family",
        "task",
        "status",
        "precision",
        "recall",
        "f1",
        "fn_rate",
        "rmse",
        "lead_hit",
        "meets_thesis",
        "trained_at",
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font

    for i, m in enumerate(list_models(db), 2):
        metrics = m.metrics or {}
        params = m.params or {}
        gates = metrics.get("gates") or {}
        ws.cell(i, 1, m.id)
        ws.cell(i, 2, m.name)
        ws.cell(i, 3, m.algorithm)
        ws.cell(i, 4, params.get("family"))
        ws.cell(i, 5, params.get("task"))
        ws.cell(i, 6, m.status)
        ws.cell(i, 7, metrics.get("precision"))
        ws.cell(i, 8, metrics.get("recall"))
        ws.cell(i, 9, metrics.get("f1"))
        ws.cell(i, 10, metrics.get("false_negative_rate"))
        ws.cell(i, 11, metrics.get("rmse"))
        ws.cell(i, 12, metrics.get("lead_time_hit_rate"))
        ws.cell(i, 13, gates.get("meets_thesis"))
        ws.cell(i, 14, m.trained_at.isoformat() if m.trained_at else None)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
