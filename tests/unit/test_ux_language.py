"""Lenguaje operativo y copy (Plan 18)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.copy import operative_strings
from ml_core.forecasting.explain.language import forbidden_in

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "app" / "templates"
SKIP_PARTS = ("laboratorio", "/ml/", "\\ml\\", "roles", "ingeniero")


def _visible_text(html: str) -> str:
    import re

    text = re.sub(r"\{\{.*?\}\}", " ", html, flags=re.S)
    text = re.sub(r"\{%.*?%\}", " ", text, flags=re.S)
    text = re.sub(r"\{#.*?#\}", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


@pytest.mark.plan18
def test_copy_has_no_forbidden_terms() -> None:
    for line in operative_strings():
        assert forbidden_in(line) == [], line


@pytest.mark.plan18
def test_operational_templates_plain_language() -> None:
    hits: list[str] = []
    for path in TEMPLATES.rglob("*.html"):
        rel = path.as_posix()
        if any(part in rel for part in ("/laboratorio/", "/ml/", "/roles/")):
            continue
        raw = path.read_text(encoding="utf-8")
        if "LAB_BADGE" in raw and "laboratorio" in rel:
            continue
        visible = _visible_text(raw)
        found = forbidden_in(visible)
        if found:
            hits.append(f"{rel}: {found}")
    assert hits == []
