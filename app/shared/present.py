"""Presentación operativa: sensores, avisos y cifras en lenguaje natural."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.catalog import repository as catalog_repo
from app.modules.forecasting import repository as forecast_repo
from app.shared import copy
from app.shared.formatting import display_gas, format_datetime_short
from ml_core.forecasting.problem import ProblemSpec

ROOT = Path(__file__).resolve().parents[2]
G0_PATH = ROOT / "reports" / "diagnostico" / "g0_decision.json"

ATTENTION_KEYS = {"vigilar", "actuar", "evacuar"}


def grid_step_minutes(db: Session | None = None) -> int:
    if db is not None:
        try:
            raw = catalog_repo.get_setting(db, "grid_step_minutes")
        except Exception:  # noqa: BLE001 — catálogo ausente en DB no migrada
            raw = None
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    spec = load_spec()
    return int(spec.grid_step_minutes)


def load_spec() -> ProblemSpec:
    if G0_PATH.exists():
        return ProblemSpec.from_g0_file(G0_PATH, lookback=60)
    return ProblemSpec(lookback=60, horizons=(6, 12, 18), grid_step_minutes=6)


def g0_context() -> dict[str, Any]:
    spec = load_spec()
    payload: dict[str, Any] = {}
    if G0_PATH.exists():
        payload = json.loads(G0_PATH.read_text(encoding="utf-8"))
    return {
        "horizons": list(spec.horizons),
        "grid_step": spec.grid_step_minutes,
        "note": copy.g0_note(list(spec.horizons)),
        "raw": payload,
    }


def present_card(card: dict[str, Any]) -> dict[str, Any]:
    level = copy.status_key(card.get("risk_level"))
    last = card.get("last_value")
    unit = card.get("unit") or "%"
    now_txt = f"{last} {unit}" if last not in (None, "") else "—"
    expected = card.get("predicted_concentration")
    expected_txt = copy.expected_around(expected, unit) if expected is not None else copy.NO_MODEL
    return {
        **card,
        "status_key": level,
        "status_word": copy.status_word(level),
        "status_icon": copy.status_icon(level),
        "now_txt": now_txt,
        "next_txt": expected_txt,
        "href": f"/sensores/{card.get('sensor_id')}",
        "zone_href": f"/zonas/{card.get('site_id')}",
    }


def attention_count(cards: list[dict[str, Any]]) -> int:
    zones: set[Any] = set()
    for card in cards:
        presented = present_card(card)
        if presented["status_key"] in ATTENTION_KEYS:
            zones.add(card.get("site_id") or card.get("sensor_id"))
    return len(zones)


def present_alert(alert: dict[str, Any]) -> dict[str, Any]:
    level = copy.status_key(alert.get("level"))
    why = alert.get("plain_message") or alert.get("message") or "Los sensores muestran un cambio en esta zona."
    action = (
        alert.get("plain_recommendation")
        or alert.get("recommendation")
        or "revisar la ventilación y preparar la salida del personal"
    )
    now_value = alert.get("now_value") or "—"
    expected = alert.get("expected_value") or "—"
    limit = alert.get("limit_value") or "—"
    minutes = alert.get("minutes")
    expected_at = alert.get("expected_at")
    if minutes is None and expected_at:
        minutes = _minutes_from(expected_at)
    kind = alert.get("kind") or "confirmado"
    texts = copy.alert_card(
        level=level,
        gas=alert.get("gas_type") or "Gas",
        zone=alert.get("site_name") or alert.get("sensor_code") or "Zona",
        minutes=minutes,
        now_value=str(now_value),
        expected=str(expected),
        limit=str(limit),
        why=str(why).rstrip("."),
        action=str(action).rstrip("."),
        kind=kind if kind in {"anticipado", "confirmado"} else "confirmado",
    )
    status_ui = {
        "abierta": "Abierto",
        "reconocida": "Visto",
        "resuelta": "Cerrado",
    }.get(alert.get("status") or "", alert.get("status") or "")
    presented = {
        **alert,
        **texts,
        "status_key": level,
        "status_word": copy.status_word(level),
        "status_icon": copy.status_icon(level),
        "status_ui": status_ui,
        "href": f"/avisos/{alert.get('id')}",
        "minutes": minutes,
    }
    for key in ("created_at", "acknowledged_at", "resolved_at", "expected_at"):
        val = presented.get(key)
        if isinstance(val, datetime):
            presented[key] = format_datetime_short(val)
    return presented


def chart_now_and_next(
    db: Session,
    sensor_id: int,
    *,
    hours: float = 1.0,
) -> dict[str, Any]:
    from app.modules.dashboard import service as dash_service
    from app.modules.sensors_ingestion.models import Sensor

    series = dash_service.series_for_sensor(db, sensor_id, hours=max(1, int(hours)))
    points = series.get("points") or []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
    measured: list[dict[str, Any]] = []
    for p in points:
        ts = _parse_ts(p.get("t"))
        if ts is None:
            continue
        if ts < cutoff and hours <= 1:
            continue
        measured.append({"t": ts.isoformat(), "v": p.get("leyendo")})
    fc = forecast_repo.latest_for_sensor(db, sensor_id)
    expected: list[dict[str, Any]] = []
    band: list[dict[str, Any]] = []
    if fc is not None:
        qs = sorted(fc.quantiles or [], key=lambda q: q.horizon_min)
        base = fc.issued_at
        if measured:
            last_t = _parse_ts(measured[-1]["t"]) or base
            last_v = measured[-1]["v"]
            expected.append({"t": last_t.isoformat(), "v": last_v})
            band.append({"t": last_t.isoformat(), "lo": last_v, "hi": last_v})
        for q in qs:
            ts = base + timedelta(minutes=int(q.horizon_min))
            expected.append({"t": ts.isoformat(), "v": q.q50})
            band.append({"t": ts.isoformat(), "lo": q.q10, "hi": q.q90})
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    gas_code = sensor.gas_type if sensor else None
    thresholds = []
    if gas_code:
        for row in catalog_repo.thresholds_for_gas(db, gas_code):
            word = copy.status_word(row.level)
            val = float(row.value)
            thresholds.append(
                {
                    "label": f"{word} · {copy.number_es(val)} %",
                    "value": val,
                    "level": copy.status_key(row.level),
                }
            )
    now = datetime.now(timezone.utc).isoformat()
    return {
        "measured": measured,
        "expected": expected,
        "band": band,
        "thresholds": thresholds,
        "now": now,
        "unit": series.get("unit") or "%",
        "gas": series.get("gas_type"),
        "has_forecast": bool(expected),
    }


def reliability_snapshot(db: Session) -> dict[str, Any]:
    from app.modules.alerts.models import AlertOutcome

    rows = db.query(AlertOutcome).all()
    if not rows:
        return {
            "has_data": False,
            "recall_phrase": "Aún no hay suficientes situaciones para hablar de anticipación.",
            "lead_phrase": "Cuando haya avisos evaluados, aquí veremos los minutos de anticipación.",
            "fa_phrase": "Todavía no contamos avisos innecesarios por turno.",
            "missed": 0,
            "timely": 0,
            "total": 0,
            "lead_avg": None,
            "trend": [],
        }
    timely = 0
    missed = 0
    fa = 0
    leads: list[float] = []
    for row in rows:
        outcome = (row.outcome or "").lower()
        if outcome in {"acierto", "timely", "a_tiempo"}:
            timely += 1
        elif outcome in {"omitido", "fn", "no_avisado"}:
            missed += 1
        elif outcome in {"falsa", "fa", "innecesario"}:
            fa += 1
        if row.lead_minutes is not None:
            leads.append(float(row.lead_minutes))
    total = max(len(rows), 1)
    per_10 = round(10 * timely / total)
    lead_avg = round(sum(leads) / len(leads)) if leads else None
    return {
        "has_data": True,
        "recall_phrase": copy.reliability_recall(per_10),
        "lead_phrase": copy.reliability_lead(lead_avg or 0),
        "fa_phrase": copy.reliability_fa(fa),
        "missed": missed,
        "timely": timely,
        "total": len(rows),
        "lead_avg": lead_avg,
        "trend": [],
    }


def data_quality(db: Session) -> dict[str, Any]:
    from sqlalchemy import func

    from app.modules.sensors_ingestion.models import DataQualityIssue, GasReading, Sensor

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    coverage = (
        db.query(Sensor.id, Sensor.code, func.count(GasReading.id))
        .outerjoin(
            GasReading,
            (GasReading.sensor_id == Sensor.id) & (GasReading.tiempo_inicio >= since),
        )
        .group_by(Sensor.id, Sensor.code)
        .all()
    )
    issues = (
        db.query(DataQualityIssue)
        .order_by(DataQualityIssue.detected_at.desc())
        .limit(50)
        .all()
    )
    return {
        "coverage": [
            {"sensor": code, "readings_24h": int(n or 0)} for _sid, code, n in coverage
        ],
        "issues": [
            {
                "code": i.code,
                "severity": i.severity,
                "when": format_datetime_short(i.detected_at),
            }
            for i in issues
        ],
        "g0": g0_context(),
    }


def list_limits(db: Session) -> list[dict[str, Any]]:
    from app.modules.catalog.models import NormativeThreshold

    rows = (
        db.query(NormativeThreshold)
        .order_by(NormativeThreshold.gas_code.asc(), NormativeThreshold.level.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "gas": display_gas(row.gas_code),
                "level": copy.status_word(row.level),
                "status_key": copy.status_key(row.level),
                "value": copy.number_es(float(row.value)),
                "source": row.source_reference,
                "verified": bool(row.verified),
                "verified_label": "Verificado" if row.verified else "Por verificar",
            }
        )
    return out


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        ts = value
    else:
        try:
            ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _minutes_from(value: Any) -> Optional[int]:
    ts = _parse_ts(value)
    if ts is None:
        return None
    delta = (ts - datetime.now(timezone.utc)).total_seconds() / 60.0
    if delta <= 0:
        return None
    return int(round(delta))
