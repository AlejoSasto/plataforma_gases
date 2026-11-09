"""Orquestación de un turno: herramientas, verificación y bloques."""

from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.assistant.grounding import check_reply, data_until_label
from app.modules.assistant.models import AssistantFeedback, AssistantTurn
from app.modules.assistant.prompts import is_plain_role, system_prompt
from app.modules.assistant.providers.base import ProviderError, ProviderUnavailable
from app.modules.assistant.tools.common import validation_error
from app.modules.assistant.tools.registry import TOOLS, declarations_for, specs_for
from app.modules.audit.service import record_audit
from app.modules.catalog.models import AppSetting
from app.modules.users.models import User
from app.shared.access import canonical_role
from app.shared.copy import (
    ASK_HISTORIC,
    ASK_LIVE,
    ASK_OFF_TOPIC,
    ASK_PROTOCOL,
    ASK_SAFETY,
)
from ml_core.forecasting.explain.language import forbidden_in

log = logging.getLogger("vigia.assistant")
BOGOTA = ZoneInfo("America/Bogota")
MAX_ROUNDS = 5
_EMAIL = re.compile(r"[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}")
_RO_ENGINE = None
_HIDDEN_KEYS = {
    "source_file",
    "file_path",
    "artifact_uri",
    "email",
    "full_name",
    "acknowledged_name",
    "usuario",
    "mlflow_run_id",
}
_EMERGENCY = (
    "olor a gas",
    "se desmayo",
    "explosion",
    "incendio",
    "no respira",
    "hay un herido",
    "alguien se desmayo",
)


class TurnFailure(Exception):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(message)


def _fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", (text or "").casefold())
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items() if key not in _HIDDEN_KEYS}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _EMAIL.sub("una persona", value)
    return value


def emergency_terms(db: Session) -> tuple[str, ...]:
    row = db.get(AppSetting, "assistant_emergency_terms")
    extra: list[str] = []
    if row is not None and isinstance(row.value, list):
        extra = [str(item) for item in row.value]
    elif row is not None and isinstance(row.value, dict):
        extra = [str(item) for item in row.value.get("terms") or []]
    return tuple(_fold(item) for item in (*_EMERGENCY, *extra))


def is_emergency(text: str, terms: tuple[str, ...]) -> bool:
    folded = _fold(text)
    return any(term and term in folded for term in terms)


def _parse_final(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if "```" in raw:
            raw = raw[: raw.rfind("```")]
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        payload = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "reply" not in payload:
        return None
    return payload


def _primary_role(user: User) -> str:
    names = list(user.role_names)
    return canonical_role(names[0]) if names else "operador"


def _template(evidence: list[dict[str, Any]], data_until: str | None) -> str:
    text = "Esto es lo que hay en los datos de este turno."
    for item in evidence:
        response = item["response"]
        if item["name"] == "buscar_avisos":
            text = (
                f"Encontré {response.get('n', 0)} avisos entre {response.get('desde')} y {response.get('hasta')}."
            )
            break
        if item["name"] == "serie_gas" and response.get("n"):
            text = (
                f"En {response.get('gas_label')} hay {response.get('n')} lecturas entre "
                f"{response.get('desde')} y {response.get('hasta')}."
            )
            break
        if response.get("nota"):
            text = str(response["nota"])
            break
    if any(item["response"].get("historic") for item in evidence):
        text = f"{text} {ASK_HISTORIC}"
    label = data_until_label(data_until)
    if label:
        text = f"{text} Datos hasta el {label}."
    return text


def _table_block(item: dict[str, Any]) -> dict[str, Any] | None:
    response = item["response"]
    avisos = response.get("avisos")
    if isinstance(avisos, list) and avisos:
        return {
            "type": "table",
            "title": "Avisos",
            "columns": ["Fecha", "Equipo", "Nivel", "Resultado"],
            "rows": [
                [
                    str(row.get("fecha") or "")[:16].replace("T", " "),
                    row.get("equipo") or "",
                    row.get("nivel") or "",
                    row.get("resultado") or "",
                ]
                for row in avisos[:50]
            ],
        }
    grupos = response.get("grupos")
    if isinstance(grupos, list) and grupos:
        return {
            "type": "table",
            "title": "Estadísticas",
            "columns": ["Grupo", "Lecturas", "Mínimo", "Máximo", "Promedio"],
            "rows": [
                [row.get("grupo"), row.get("n"), row.get("min"), row.get("max"), row.get("avg")]
                for row in grupos[:50]
            ],
        }
    return None


def _blocks(
    include: list[Any],
    evidence: list[dict[str, Any]],
    charts: dict[str, Any],
    reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted = {str(item) for item in include}
    blocks: list[dict[str, Any]] = []
    for chart_id, payload in charts.items():
        if chart_id not in wanted:
            continue
        blocks.append(
            {
                "type": "chart",
                "chart_id": chart_id,
                "kind": payload.get("kind"),
                "title": payload.get("title"),
                "data_url": f"/api/asistente/graficos/{chart_id}",
            }
        )
    for report in reports:
        if str(report.get("report_id")) not in wanted:
            continue
        blocks.append(
            {
                "type": "report",
                "report_id": report.get("report_id"),
                "format": report.get("format") or "pdf",
                "title": report.get("title") or "Informe",
                "download_url": report.get("download_url"),
            }
        )
    for item in evidence:
        evidence_id = str(item["response"].get("evidence_id") or "")
        if evidence_id not in wanted:
            continue
        table = _table_block(item)
        if table:
            blocks.append(table)
        for row in item["response"].get("avisos") or []:
            aviso = row.get("aviso")
            if aviso is None:
                continue
            blocks.append({"type": "link", "title": f"Ver aviso {aviso}", "url": f"/avisos/{aviso}"})
        for fragment in item["response"].get("fragmentos") or []:
            blocks.append(
                {
                    "type": "manual",
                    "title": fragment.get("titulo") or "Manual",
                    "url": fragment.get("url") or "/ayuda",
                }
            )
    return blocks


def _read_session(fallback: Session) -> tuple[Session, bool]:
    """Si hay ASSISTANT_DATABASE_URL, las lecturas van por ese usuario (solo lectura)."""
    global _RO_ENGINE
    url = (settings.assistant_database_url or "").strip()
    if not url:
        return fallback, False
    if _RO_ENGINE is None:
        from sqlalchemy import create_engine

        _RO_ENGINE = create_engine(url, pool_pre_ping=True)
    return Session(bind=_RO_ENGINE), True


def _execute(db: Session, user: User, name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    allowed = {spec.name for spec in specs_for(user)}
    spec = TOOLS.get(name)
    if spec is None or name not in allowed:
        return {"error": "No puedes consultar eso con tu rol.", "_denied": True}
    try:
        params = spec.model.model_validate(args or {})
    except ValidationError as exc:
        return validation_error(exc)
    try:
        payload = spec.fn(db, user, params, ctx)
    except Exception:  # noqa: BLE001 — la herramienta nunca revienta hacia el cliente
        log.exception("herramienta %s falló", name)
        return {"error": "No pude consultar esos datos. Intenta con otro periodo."}
    if not isinstance(payload, dict):
        return {"error": "No pude consultar esos datos."}
    return _redact(payload)


def _polish(reply: str, question: str, evidence: list[dict[str, Any]], data_until: str | None) -> str:
    historic = any(item["response"].get("historic") for item in evidence)
    folded = _fold(reply)
    if historic and "historic" not in folded:
        reply = f"{reply} {ASK_HISTORIC}"
    elif evidence and not historic and "en vivo" not in folded and "datos hasta" in folded:
        reply = f"{reply} {ASK_LIVE}"
    label = data_until_label(data_until)
    if label and "datos hasta" not in _fold(reply):
        reply = f"{reply} Datos hasta el {label}."
    if ("que hacer" in _fold(question) or "qué hacer" in question.casefold()) and ASK_PROTOCOL not in reply:
        reply = f"{reply} {ASK_PROTOCOL}"
    if ("es seguro" in _fold(question) or "seguro entrar" in _fold(question)) and "no puedo decidir" not in _fold(reply):
        reply = f"{ASK_SAFETY} {reply}"
    return reply.strip()


def _sources(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for item in evidence:
        response = item["response"]
        rows = response.get("n")
        if rows is None:
            rows = response.get("n_grupos")
        if rows is None and isinstance(response.get("avisos"), list):
            rows = len(response["avisos"])
        if rows is None and isinstance(response.get("equipos"), list):
            rows = len(response["equipos"])
        sources.append(
            {
                "tool": item["name"],
                "params": item.get("args") or {},
                "rows": int(rows or 0),
            }
        )
    return sources


def _purge(db: Session) -> None:
    days = int(settings.assistant_retention_days or 90)
    row = db.get(AppSetting, "assistant_retention_days")
    if row is not None and isinstance(row.value, dict) and row.value.get("days"):
        days = int(row.value["days"])
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db.query(AssistantTurn).filter(AssistantTurn.created_at < cutoff).delete(synchronize_session=False)


def _save(
    db: Session,
    *,
    user: User,
    role: str,
    question: str,
    evidence: list[dict[str, Any]],
    charts: dict[str, Any],
    reply: str,
    grounded: bool,
    in_scope: bool,
    latency_ms: int,
    provider: str,
    model: str,
    tokens: int | None,
) -> str:
    turn_id = "t_" + uuid4().hex[:8]
    safe_tools = [
        {"tool": item["name"], "params": item.get("args") or {}, "rows": _sources([item])[0]["rows"]}
        for item in evidence
    ]
    row = AssistantTurn(
        id=turn_id,
        user_id=user.id,
        role=role,
        question=question[:2000],
        tools=safe_tools,
        artifacts={"charts": charts},
        grounded=grounded,
        in_scope=in_scope,
        latency_ms=latency_ms,
        provider=provider,
        model=model[:128],
        tokens=tokens,
        reply=reply,
    )
    db.add(row)
    short = " ".join(question.split())
    if len(short) > 140:
        short = short[:137] + "…"
    details = f"preguntó: {short}"
    if any(item["name"] == "generar_informe" and not item["response"].get("error") for item in evidence):
        details += " y generó un informe PDF"
    record_audit(
        db,
        action="assistant.ask",
        user_id=user.id,
        resource_type="assistant_turn",
        resource_id=turn_id,
        metadata={"grounded": grounded, "in_scope": in_scope, "tools": [item["name"] for item in evidence]},
        details=details,
    )
    db.commit()
    return turn_id


def run_turn(
    db: Session,
    user: User,
    messages: list[dict[str, str]],
    *,
    provider: Any,
) -> dict[str, Any]:
    started = time.monotonic()
    question = messages[-1]["content"]
    role = _primary_role(user)
    read_db, close_read = _read_session(db)
    try:
        return _run_turn_body(db, read_db, user, messages, provider, started, question, role)
    finally:
        if close_read:
            read_db.close()


def _run_turn_body(
    db: Session,
    read_db: Session,
    user: User,
    messages: list[dict[str, str]],
    provider: Any,
    started: float,
    question: str,
    role: str,
) -> dict[str, Any]:
    _purge(db)
    if is_emergency(question, emergency_terms(db)):
        from app.shared.copy import ASK_EMERGENCY

        reply = ASK_EMERGENCY
        turn_id = _save(
            db,
            user=user,
            role=role,
            question=question,
            evidence=[],
            charts={},
            reply=reply,
            grounded=True,
            in_scope=True,
            latency_ms=int((time.monotonic() - started) * 1000),
            provider="none",
            model="",
            tokens=0,
        )
        return {
            "reply": reply,
            "in_scope": True,
            "data_until": None,
            "blocks": [],
            "sources": [],
            "turn_id": turn_id,
            "grounded": True,
        }

    deadline = started + float(settings.assistant_turn_timeout_s or 60)
    today = datetime.now(BOGOTA).date().isoformat()
    data_until = None
    system = system_prompt(role=role, fecha_hoy=today, datos_hasta="se consulta con herramientas")
    tools = declarations_for(user)
    evidence: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    ctx: dict[str, Any] = {"evidence": [], "charts": {}, "reports": [], "series": {}}
    correction: str | None = None
    grounded = True
    in_scope = True
    include: list[Any] = []
    reply = ""
    tokens = 0
    model = getattr(provider, "model", "")
    rounds = 0
    reply_tries = 0
    ground_retries = 0
    language_retries = 0
    provider_errors = 0
    plain = is_plain_role(role)

    while rounds <= MAX_ROUNDS and reply_tries < 4:
        if time.monotonic() > deadline:
            break
        try:
            result = provider.generate(
                system=system,
                messages=messages,
                tools=tools,
                pending=pending,
                correction=correction,
            )
        except ProviderUnavailable as exc:
            raise TurnFailure(503, "El asistente no está disponible sin conexión. Puedes usar los filtros de cada pantalla.") from exc
        except ProviderError as exc:
            provider_errors += 1
            log.warning("proveedor: %s", exc)
            if provider_errors > 1:
                raise TurnFailure(502, "No pude completar la consulta. Intenta de nuevo.") from exc
            continue
        model = result.model or model
        if result.tokens:
            tokens += int(result.tokens)
        correction = None
        if result.calls:
            if rounds >= MAX_ROUNDS:
                break
            for call in result.calls:
                name = str(call.get("name") or "")
                args = call.get("args") or {}
                if not isinstance(args, dict):
                    args = {}
                session = db if name == "generar_informe" else read_db
                payload = _execute(session, user, name, args, ctx)
                if payload.pop("_denied", False):
                    record_audit(
                        db,
                        action="assistant.tool_denied",
                        user_id=user.id,
                        resource_type="assistant_tool",
                        resource_id=name,
                    )
                payload["evidence_id"] = payload.get("evidence_id") or f"e_{len(evidence) + 1}"
                if payload.get("data_until"):
                    data_until = str(payload["data_until"])
                item = {"name": name, "args": args, "response": payload}
                evidence.append(item)
                ctx["evidence"].append(payload)
                pending.append(item)
            rounds += 1
            system = system_prompt(
                role=role,
                fecha_hoy=today,
                datos_hasta=data_until or "se consulta con herramientas",
            )
            continue
        parsed = _parse_final(result.text)
        reply_tries += 1
        if parsed is None:
            if reply_tries >= 2:
                raise TurnFailure(502, "No pude completar la consulta. Intenta de nuevo.")
            correction = "Responde solo con el objeto JSON pedido, usando los resultados de las herramientas."
            continue
        reply = str(parsed.get("reply") or "").strip()
        in_scope = bool(parsed.get("in_scope", True))
        include = list(parsed.get("include") or [])
        if not in_scope:
            reply = ASK_OFF_TOPIC
            grounded = True
            break
        blobs: list[Any] = [item["response"] for item in evidence]
        blobs.append(data_until or "")
        blobs.extend(item.get("args") or {} for item in evidence)
        bad = check_reply(reply, *blobs)
        if bad:
            if ground_retries < 1:
                ground_retries += 1
                correction = f"La cifra {bad} no está en los datos; corrige usando solo los resultados"
                grounded = False
                continue
            reply = _template(evidence, data_until)
            grounded = False
        else:
            grounded = True
        if plain and forbidden_in(reply):
            if language_retries < 1:
                language_retries += 1
                correction = "Reformula la respuesta en lenguaje sencillo, sin términos técnicos, y sin cifras nuevas."
                continue
            reply = _template(evidence, data_until)
            grounded = check_reply(reply, *blobs) is None
        break
    else:
        if not reply:
            reply = _template(evidence, data_until)

    if not reply:
        reply = _template(evidence, data_until)
        grounded = False
    if in_scope:
        reply = _polish(reply, question, evidence, data_until)
        blobs = [item["response"] for item in evidence]
        blobs.append(data_until or "")
        if check_reply(reply, *blobs):
            reply = _template(evidence, data_until)
            reply = _polish(reply, question, evidence, data_until)
            grounded = False
        if plain and forbidden_in(reply):
            reply = _template(evidence, data_until)
            grounded = False

    blocks = _blocks(include, evidence, ctx["charts"], ctx["reports"]) if in_scope else []
    turn_id = _save(
        db,
        user=user,
        role=role,
        question=question,
        evidence=evidence,
        charts=ctx["charts"],
        reply=reply,
        grounded=grounded,
        in_scope=in_scope,
        latency_ms=int((time.monotonic() - started) * 1000),
        provider=getattr(provider, "name", "unknown"),
        model=model or "",
        tokens=tokens or None,
    )
    return {
        "reply": reply,
        "in_scope": in_scope,
        "data_until": data_until,
        "blocks": blocks,
        "sources": _sources(evidence) if in_scope else [],
        "turn_id": turn_id,
        "grounded": grounded,
    }


def save_feedback(db: Session, user: User, turn_id: str, *, useful: bool, comment: str | None) -> None:
    turn = db.get(AssistantTurn, turn_id)
    if turn is None or turn.user_id != user.id:
        raise TurnFailure(404, "No encuentro esa respuesta.")
    db.add(AssistantFeedback(turn_id=turn_id, useful=useful, comment=comment))
    db.commit()


def chart_payload(db: Session, user: User, chart_id: str) -> dict[str, Any] | None:
    rows = (
        db.query(AssistantTurn)
        .filter(AssistantTurn.user_id == user.id)
        .order_by(AssistantTurn.created_at.desc())
        .limit(30)
        .all()
    )
    for row in rows:
        charts = (row.artifacts or {}).get("charts") or {}
        if chart_id in charts:
            return charts[chart_id]
    return None
