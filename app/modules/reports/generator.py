"""Generadores de reportes PDF (ReportLab) y Excel (openpyxl).

Paleta alineada con tokens de interfaz (Plan 18):
  accent #1E3A5F, estados operativo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib.units import cm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.alerts import service as alerts_service
from app.modules.alerts.models import Alert
from app.modules.ml_training.repository import get_model, list_models
from app.modules.reports import pdf_theme as theme
from app.modules.sensors_ingestion.models import GasReading, Sensor
from app.modules.stakeholders.service import alert_ids_visible_to_user
from app.shared import copy
from app.shared.present import reliability_snapshot


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


def _level_pairs(levels: list[str]) -> list[tuple[str, int]]:
    order = ["evacuar", "actuar", "vigilar", "normal"]
    counts = {copy.status_word(key): 0 for key in order}
    for level in levels:
        word = copy.status_word(copy.status_key(level))
        counts[word] = counts.get(word, 0) + 1
    return [(copy.status_word(key), counts[copy.status_word(key)]) for key in order]


def _site_pairs(names: list[str], limit: int = 8) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for name in names:
        label = name or "Sin zona"
        counts[label] = counts.get(label, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:limit]


def _when(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value or "")[:16]


def _footer(start: datetime, end: datetime, who: str, *, origin: str | None = None) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f"Periodo {start.date().isoformat()} a {end.date().isoformat()}. "
        f"Datos hasta {generated}."
    )
    if origin:
        text += f" Origen: {origin}."
    return f"{text} Generado por {who}."


def _story_avisos(
    rows: list[dict[str, Any]],
    start: datetime,
    end: datetime,
    *,
    zone_heading: str = copy.PDF_BY_ZONE,
) -> list[Any]:
    levels = _level_pairs([str(row.get("level") or "") for row in rows])
    sites = _site_pairs([str(row.get("site") or "Sin zona") for row in rows])
    closed = [row["hours"] for row in rows if isinstance(row.get("hours"), (int, float))]
    avg_h = round(sum(closed) / len(closed), 2) if closed else None
    lead = copy.PDF_AVISOS_COUNT.format(n=len(rows)) if rows else copy.PDF_AVISOS_EMPTY
    story: list[Any] = [
        theme.paragraph(copy.PDF_AVISOS_TITLE, "title"),
        theme.paragraph(lead),
        theme.paragraph(f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}", "muted"),
        theme.spacer(8),
        theme.kpis(
            [
                (copy.PDF_TOTAL, str(len(rows))),
                (
                    copy.PDF_CLOSE_TIME,
                    copy.PDF_HOURS.format(n=copy.number_es(avg_h, 1)) if avg_h is not None else copy.PDF_NO_CLOSE,
                ),
                (zone_heading, str(len(sites))),
            ]
        ),
        theme.paragraph(copy.PDF_BY_LEVEL, "h2"),
    ]
    chart = theme.bars(levels, fills=theme.status_fills([label for label, _count in levels]), unit="Avisos")
    if chart is not None:
        story.append(chart)
    if sites:
        story.append(theme.paragraph(zone_heading, "h2"))
        zone_chart = theme.bars(sites, unit="Avisos")
        if zone_chart is not None:
            story.append(zone_chart)
    story.append(theme.paragraph(copy.PDF_DETAIL, "h2"))
    table = [["Fecha", "Zona", "Equipo", "Nivel", "Estado"]]
    for row in rows[:500]:
        table.append(
            [
                row.get("when") or "—",
                row.get("site") or "—",
                row.get("sensor") or "—",
                copy.status_word(copy.status_key(str(row.get("level") or ""))),
                theme.state_word(row.get("status")),
            ]
        )
    if len(table) == 1:
        table.append(["—", "—", "—", "—", copy.PDF_AVISOS_EMPTY])
    story.append(theme.data_table(table, [3.1 * cm, 3.6 * cm, 3.4 * cm, 2.8 * cm, 4.5 * cm]))
    return story


def _alert_rows(db: Session, alerts: list[Alert]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for alert in alerts:
        data = alerts_service.alert_to_dict(db, alert)
        hours = None
        if alert.resolved_at and alert.created_at:
            hours = (alert.resolved_at - alert.created_at).total_seconds() / 3600.0
        rows.append(
            {
                "level": data.get("level"),
                "site": data.get("site_name") or "Sin zona",
                "sensor": data.get("sensor_code") or "",
                "status": data.get("status"),
                "when": _when(data.get("created_at")),
                "hours": hours,
            }
        )
    return rows


def generate_alertas_periodo(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    visible_ids: Optional[set[int]] = None,
    who: str = "Vigía",
) -> bytes:
    alerts = _query_alerts(db, start, end, visible_ids=visible_ids)
    story = _story_avisos(_alert_rows(db, alerts), start, end)
    return theme.render(story, title=copy.PDF_AVISOS_TITLE, footer=_footer(start, end, who))


def generate_confiabilidad(db: Session, *, who: str = "Vigía") -> bytes:
    snap = reliability_snapshot(db)
    pairs = [
        (copy.PDF_ON_TIME, int(snap.get("timely") or 0)),
        (copy.PDF_MISSED, int(snap.get("missed") or 0)),
        (copy.PDF_UNNECESSARY, int(snap.get("unnecessary") or 0)),
    ]
    today = datetime.now(timezone.utc)
    story: list[Any] = [
        theme.paragraph(copy.PDF_CONFIABILIDAD_TITLE, "title"),
        theme.paragraph(copy.PDF_CONFIABILIDAD_LEAD),
        theme.spacer(8),
        theme.kpis(
            [
                (copy.PDF_SAMPLE, str(snap.get("total") or 0)),
                (copy.PDF_ON_TIME, str(snap.get("timely") or 0)),
                (copy.PDF_MISSED, str(snap.get("missed") or 0)),
            ]
        ),
        theme.paragraph(snap.get("recall_phrase") or "", ),
        theme.paragraph(snap.get("lead_phrase") or ""),
        theme.paragraph(snap.get("fa_phrase") or ""),
        theme.paragraph(copy.PDF_BY_LEVEL, "h2"),
    ]
    chart = theme.bars(
        pairs,
        fills=[theme.STATUS_COLOR["normal"], theme.STATUS_COLOR["evacuar"], theme.STATUS_COLOR["vigilar"]],
        unit="Avisos",
    )
    if chart is not None:
        story.append(chart)
    return theme.render(
        story,
        title=copy.PDF_CONFIABILIDAD_TITLE,
        footer=_footer(today, today, who, origin="avisos ya evaluados"),
    )


def _gas_counts(db: Session, start: datetime, end: datetime) -> list[tuple[str, int]]:
    from app.shared.gas_catalog import display_gas

    start_b, end_b = _period_bounds(start, end)
    rows = (
        db.query(Sensor.gas_type, func.count(GasReading.id))
        .join(GasReading, GasReading.sensor_id == Sensor.id)
        .filter(GasReading.tiempo_inicio >= start_b, GasReading.tiempo_inicio <= end_b)
        .group_by(Sensor.gas_type)
        .all()
    )
    return [(display_gas(gas), int(count)) for gas, count in rows]


def generate_resumen_pdf(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    stakeholder_id: Optional[int] = None,
    user_id: Optional[int] = None,
    who: str = "Vigía",
) -> bytes:
    alerts = _alerts_for_resumen(db, start, end, stakeholder_id=stakeholder_id, user_id=user_id)
    rows = _alert_rows(db, alerts)
    snap = reliability_snapshot(db)
    gases = _gas_counts(db, start, end)
    story = _story_avisos(rows, start, end)
    story[0] = theme.paragraph(copy.PDF_GERENCIA_TITLE, "title")
    story.insert(
        1,
        theme.paragraph(
            copy.PDF_GERENCIA_LEAD.format(inicio=start.strftime("%d/%m/%Y"), fin=end.strftime("%d/%m/%Y"))
        ),
    )
    extra: list[Any] = [
        theme.paragraph(snap.get("recall_phrase") or ""),
        theme.paragraph(snap.get("lead_phrase") or ""),
        theme.paragraph(copy.PDF_BY_GAS, "h2"),
    ]
    gas_chart = theme.bars(gases, unit="Lecturas") if gases else None
    extra.append(gas_chart if gas_chart is not None else theme.paragraph("Sin lecturas en el periodo.", "muted"))
    story = story[:-2] + extra + story[-2:]
    return theme.render(story, title=copy.PDF_GERENCIA_TITLE, footer=_footer(start, end, who))


def _metric_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _matrix_rows(data: Any) -> list[list[str]]:
    if isinstance(data, list) and data and isinstance(data[0], list):
        width = max(len(row) for row in data)
        header = [" "] + [str(index) for index in range(width)]
        body = []
        for index, row in enumerate(data):
            cells = [str(cell) for cell in row] + [""] * (width - len(row))
            body.append([str(index), *cells])
        return [header, *body]
    if isinstance(data, dict):
        return [["Clave", "Valor"], *[[str(key), str(value)] for key, value in data.items()]]
    return [["Valor"], [str(data)]]


def generate_desempeno_modelo(db: Session, model_registry_id: int) -> bytes:
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
    metric_keys = (
        "precision",
        "recall",
        "f1",
        "f1_score",
        "false_negative_rate",
        "rmse",
        "mae",
        "accuracy",
        "roc_auc",
        "lead_time_hit_rate",
    )
    rows = [["Métrica", "Valor"]]
    chart_pairs: list[tuple[str, float]] = []
    for key in metric_keys:
        if key in metrics and isinstance(metrics[key], (int, float)):
            rows.append([key, _metric_value(metrics[key])])
            chart_pairs.append((key, float(metrics[key])))
    if len(rows) == 1:
        for key, value in metrics.items():
            if key in ("gates", "thresholds", "confusion_matrix", "confusion"):
                continue
            rows.append([str(key), _metric_value(value)])
    trained = model.trained_at.isoformat() if model.trained_at else "sin fecha"
    story: list[Any] = [
        theme.paragraph("Informe técnico del registro", "title"),
        theme.paragraph(f"{model.name} v{model.version} · {model.algorithm} · {model.status}"),
        theme.paragraph(f"Entrenado: {trained}", "muted"),
        theme.paragraph("Métricas", "h2"),
    ]
    chart = theme.bars(chart_pairs, unit="Valor") if chart_pairs else None
    if chart is not None:
        story.append(chart)
    story.append(theme.data_table(rows, [9 * cm, 8 * cm]))
    gates = metrics.get("gates") or {}
    if gates:
        story.append(theme.paragraph("Criterios", "h2"))
        gate_rows = [["Criterio", "Cumple"]]
        for key, value in gates.items():
            gate_rows.append([str(key), "Sí" if value else ("N/A" if value is None else "No")])
        story.append(theme.data_table(gate_rows, [9 * cm, 8 * cm]))
    matrix = metrics.get("confusion_matrix") or metrics.get("confusion")
    story.append(theme.paragraph("Matriz de confusión", "h2"))
    if matrix:
        matrix_rows = _matrix_rows(matrix)
        width = 17 / max(len(matrix_rows[0]), 1)
        story.append(theme.data_table(matrix_rows, [width * cm] * len(matrix_rows[0])))
    else:
        story.append(theme.paragraph("No está guardada en este registro.", "muted"))
    story.append(theme.paragraph("Comparación con el registro anterior", "h2"))
    if prev is None:
        story.append(theme.paragraph("No hay otro registro con el mismo alcance."))
    else:
        prev_metrics = prev.metrics or {}
        compare = [["Métrica", "Actual", "Anterior"]]
        for key in ("precision", "recall", "f1", "f1_score"):
            current = metrics.get(key)
            previous = prev_metrics.get(key)
            if current is None and previous is None:
                continue
            compare.append(
                [
                    key,
                    _metric_value(current) if current is not None else "—",
                    _metric_value(previous) if previous is not None else "—",
                ]
            )
        if len(compare) == 1:
            compare.append(["—", "—", "—"])
        story.append(theme.data_table(compare, [5.6 * cm, 5.7 * cm, 5.7 * cm]))
        story.append(
            theme.paragraph(
                f"Anterior: {prev.name} v{prev.version} · {prev.algorithm} · {prev.status}",
                "muted",
            )
        )
    today = datetime.now(timezone.utc)
    return theme.render(
        story,
        title="Informe técnico del registro",
        footer=_footer(today, today, "Área técnica"),
    )


def _alerts_for_resumen(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    stakeholder_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> list[Alert]:
    visible: Optional[set[int]] = None
    if user_id is not None:
        visible = alert_ids_visible_to_user(db, user_id)
    alerts = _query_alerts(db, start, end, visible_ids=visible)
    if stakeholder_id is None:
        return alerts
    from app.modules.stakeholders.models import StakeholderSubscription
    from app.modules.stakeholders.service import LEVEL_RANK

    subs = (
        db.query(StakeholderSubscription)
        .filter(StakeholderSubscription.stakeholder_id == stakeholder_id)
        .all()
    )
    if not subs:
        return []
    filtered: list[Alert] = []
    for alert in alerts:
        sensor = db.query(Sensor).filter(Sensor.id == alert.sensor_id).first()
        site_id = sensor.site_id if sensor else None
        for sub in subs:
            if LEVEL_RANK.get(alert.level, 0) < LEVEL_RANK.get(sub.min_level, 0):
                continue
            if sub.sensor_id and sub.sensor_id != alert.sensor_id:
                continue
            if sub.site_id and sub.site_id != site_id:
                continue
            filtered.append(alert)
            break
    return filtered


def generate_resumen_ejecutivo(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    stakeholder_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> bytes:
    """Excel con avisos por sitio, tendencia y recomendaciones."""
    alerts = _alerts_for_resumen(db, start, end, stakeholder_id=stakeholder_id, user_id=user_id)

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
