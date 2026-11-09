"""HTTP del asistente, el manual y los gráficos del turno."""

from __future__ import annotations

import html
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from app.core.config import settings
from app.core.rate_limit import too_many
from app.modules.assistant.grounding import data_until_label
from app.modules.assistant.manual_index import get_index, search
from app.modules.assistant.providers import get_provider
from app.modules.assistant.providers.base import ProviderUnavailable
from app.modules.assistant.schemas import AskBody, FeedbackBody
from app.modules.assistant.scope import visible_sensor_ids
from app.modules.assistant.service import TurnFailure, chart_payload, run_turn, save_feedback
from app.modules.dashboard.nav import template_context
from app.modules.sensors_ingestion import query as readings
from app.shared import copy
from app.shared.access import canonical_role
from app.shared.dependencies import CurrentUser, DbSession, get_current_user
from app.shared.exceptions import UnauthorizedError
from app.shared.templating import make_templates

router = APIRouter(tags=["asistente"])
TEMPLATES = make_templates()
_MANUAL = Path(__file__).resolve().parents[3] / "docs" / "manual"


def _offline() -> JSONResponse:
    return JSONResponse({"error": copy.ASK_OFFLINE}, status_code=503)


def _user(request: Request, db: DbSession):
    try:
        return get_current_user(request, db)
    except UnauthorizedError:
        return None


@router.post("/api/asistente")
async def preguntar(request: Request, db: DbSession) -> JSONResponse:
    raw = await request.body()
    if len(raw) > 32 * 1024:
        return JSONResponse({"error": "La pregunta es demasiado larga."}, status_code=400)
    user = _user(request, db)
    if user is None:
        return JSONResponse({"error": "Necesitas ingresar para preguntar."}, status_code=401)
    if (settings.assistant_provider or "off") == "off":
        return _offline()
    if too_many(f"asistente:{user.id}", limit=20, window_s=60):
        return JSONResponse(
            {"error": "Hiciste muchas preguntas seguidas. Espera un minuto."},
            status_code=429,
        )
    try:
        body = AskBody.model_validate_json(raw)
    except ValidationError:
        return JSONResponse(
            {"error": "La pregunta no tiene el formato esperado. El último mensaje debe ser tuyo."},
            status_code=400,
        )
    try:
        provider = get_provider()
    except ProviderUnavailable:
        return _offline()
    messages = [item.model_dump() for item in body.messages]
    try:
        result = run_turn(db, user, messages, provider=provider)
    except TurnFailure as exc:
        return JSONResponse({"error": exc.message}, status_code=exc.status)
    result.pop("grounded", None)
    return JSONResponse(result)


@router.get("/api/asistente/sugerencias")
def sugerencias(request: Request, db: DbSession) -> JSONResponse:
    user = _user(request, db)
    if user is None:
        return JSONResponse({"error": "Necesitas ingresar para preguntar."}, status_code=401)
    if (settings.assistant_provider or "off") == "off":
        return _offline()
    ids = visible_sensor_ids(db, user)
    _start, end = readings.data_bounds(db, ids)
    label = data_until_label(end) if end else "la última lectura cargada"
    role = canonical_role(next(iter(user.role_names), "operador"))
    month = ""
    if end is not None:
        months = (
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        )
        month = f"{months[end.month - 1]} de {end.year}"
    bank = {
        "operador": [
            "¿Qué avisos hubo en el último turno con datos?",
            "¿Cómo cierro un aviso?",
        ],
        "supervisor_seguridad": [
            f"Avisos de ácido sulfhídrico de {month}" if month else "Avisos de ácido sulfhídrico del último mes con datos",
            "Genera el informe de avisos de ese mes en PDF",
        ],
        "gerencia": [
            "¿Qué tan confiable es el sistema?",
            "Resumen para gerencia del último trimestre con datos",
        ],
        "analista": [
            "¿Qué modelo ganó en metano a 12 minutos y por qué?",
        ],
        "auditor": [
            "¿Qué avisos hubo en el último mes con datos?",
            "¿Cómo se lee un aviso?",
        ],
        "admin": [
            "¿Qué avisos hubo en el último mes con datos?",
            "¿Cómo cierro un aviso?",
        ],
    }
    return JSONResponse(
        {
            "data_until": end.isoformat() if end else None,
            "data_until_label": label,
            "welcome": copy.ASK_WELCOME.format(fecha=label),
            "items": bank.get(role, bank["operador"]),
        }
    )


@router.post("/api/asistente/{turn_id}/valoracion")
async def valorar(turn_id: str, request: Request, db: DbSession) -> JSONResponse:
    user = _user(request, db)
    if user is None:
        return JSONResponse({"error": "Necesitas ingresar para preguntar."}, status_code=401)
    try:
        body = FeedbackBody.model_validate_json(await request.body())
    except ValidationError:
        return JSONResponse({"error": "No pude guardar la valoración."}, status_code=400)
    try:
        save_feedback(db, user, turn_id, useful=body.util, comment=body.comentario)
    except TurnFailure as exc:
        return JSONResponse({"error": exc.message}, status_code=exc.status)
    return JSONResponse({"ok": True})


@router.get("/api/asistente/graficos/{chart_id}")
def grafico(chart_id: str, request: Request, db: DbSession) -> JSONResponse:
    user = _user(request, db)
    if user is None:
        return JSONResponse({"error": "Necesitas ingresar para preguntar."}, status_code=401)
    payload = chart_payload(db, user, chart_id)
    if payload is None:
        return JSONResponse({"error": "No encuentro ese gráfico."}, status_code=404)
    return JSONResponse(payload)


def _render_md(body: str) -> str:
    chunks: list[str] = []
    in_list = False
    for line in body.splitlines():
        image = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if line.startswith("## "):
            if in_list:
                chunks.append("</ul>")
                in_list = False
            title = line[3:].strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
            chunks.append(f'<h2 id="{html.escape(anchor)}">{html.escape(title)}</h2>')
        elif line.startswith("# "):
            chunks.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("- "):
            if not in_list:
                chunks.append("<ul>")
                in_list = True
            chunks.append(f"<li>{html.escape(line[2:].strip())}</li>")
        elif image:
            if in_list:
                chunks.append("</ul>")
                in_list = False
            alt, src = image.group(1), image.group(2)
            if src.startswith("img/"):
                src = "/ayuda-img/" + src[4:]
            chunks.append(
                f'<figure class="manual-fig"><img src="{html.escape(src)}" alt="{html.escape(alt)}"></figure>'
            )
        elif line.strip() == "":
            if in_list:
                chunks.append("</ul>")
                in_list = False
        else:
            if in_list:
                chunks.append("</ul>")
                in_list = False
            chunks.append(f"<p>{html.escape(line.strip())}</p>")
    if in_list:
        chunks.append("</ul>")
    return "\n".join(chunks)


@router.get("/ayuda", response_class=HTMLResponse)
def ayuda_indice(request: Request, user: CurrentUser, q: str = "") -> HTMLResponse:
    role = canonical_role(next(iter(user.role_names), "operador"))
    index = get_index()
    pages = []
    seen: set[str] = set()
    for section in index.sections:
        if section.slug in seen:
            continue
        if role != "admin" and role not in section.roles:
            continue
        seen.add(section.slug)
        pages.append({"slug": section.slug, "title": section.title})
    hits = search(q, role=role, limit=5) if q.strip() else []
    ctx = template_context(user, title="Ayuda", active_nav="ayuda")
    return TEMPLATES.TemplateResponse(
        request,
        "ayuda/index.html",
        {**ctx, "pages": pages, "query": q, "hits": hits},
    )


@router.get("/ayuda/{slug}", response_class=HTMLResponse)
def ayuda_pagina(slug: str, request: Request, user: CurrentUser) -> HTMLResponse:
    role = canonical_role(next(iter(user.role_names), "operador"))
    sections = [
        section
        for section in get_index().sections
        if section.slug == slug and (role == "admin" or role in section.roles)
    ]
    if not sections:
        return TEMPLATES.TemplateResponse(
            request,
            "errors/404.html",
            {"title": "No encontrado", "current_user": user, "sala": False},
            status_code=404,
        )
    path = next(_MANUAL.glob(f"*_{slug.replace('-', '_')}.md"), None)
    if path is None:
        path = next(_MANUAL.glob(f"*{slug}.md"), None)
    raw = path.read_text(encoding="utf-8") if path else ""
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        raw = raw[end + 4 :] if end >= 0 else raw
    ctx = template_context(user, title=sections[0].title, active_nav="ayuda")
    return TEMPLATES.TemplateResponse(
        request,
        "ayuda/page.html",
        {**ctx, "page_title": sections[0].title, "body_html": _render_md(raw)},
    )


@router.get("/ayuda-img/{name}")
def ayuda_img(name: str):
    from fastapi.responses import FileResponse

    safe = Path(name).name
    path = _MANUAL / "img" / safe
    if not path.is_file():
        return JSONResponse({"error": "No encuentro esa imagen."}, status_code=404)
    return FileResponse(path)
