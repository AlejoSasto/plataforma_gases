"""Verificador de lenguaje operativo (Plan 17 / 18 / 20)."""

from __future__ import annotations

import re
import unicodedata

from app.shared.copy import FORBIDDEN_TERMS

__all__ = ["FORBIDDEN_TERMS", "forbidden_in", "assert_plain"]


def _fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def forbidden_in(text: str) -> list[str]:
    folded = _fold(text)
    hits: list[str] = []
    for term in FORBIDDEN_TERMS:
        pat = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
        if re.search(pat, folded):
            hits.append(term)
    return hits


def assert_plain(text: str) -> None:
    hits = forbidden_in(text)
    if hits:
        raise AssertionError(f"términos prohibidos en texto operativo: {hits} | {text}")
