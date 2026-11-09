"""Jinja2 con copy y filtros de la operación."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.shared import copy
from app.shared.freshness import data_as_of_label

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def make_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["copy"] = copy
    templates.env.globals["C"] = copy
    templates.env.globals["data_as_of_label"] = data_as_of_label
    templates.env.globals["assistant_on"] = lambda: (settings.assistant_provider or "off") != "off"
    templates.env.filters["status_word"] = copy.status_word
    templates.env.filters["status_key"] = copy.status_key
    templates.env.filters["status_icon"] = copy.status_icon
    templates.env.filters["es_num"] = copy.number_es
    return templates
