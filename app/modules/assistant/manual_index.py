"""Índice BM25 del manual. Se arma en el proceso, sin internet ni embeddings."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

_TOKEN = re.compile(r"[a-záéíóúüñ0-9]{3,}", re.IGNORECASE)
_ROOT = Path(__file__).resolve().parents[3] / "docs" / "manual"


def fold(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(fold(text))


@dataclass
class Section:
    slug: str
    title: str
    heading: str
    anchor: str
    body: str
    roles: set[str]
    screens: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        if self.anchor:
            return f"/ayuda/{self.slug}#{self.anchor}"
        return f"/ayuda/{self.slug}"


def _split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end < 0:
        return {}, raw
    meta: dict[str, str] = {}
    for line in raw[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, raw[end + 4 :].lstrip()


def _list_field(value: str) -> list[str]:
    text = value.strip().strip("[]")
    if not text:
        return []
    return [part.strip().strip("\"'") for part in text.split(",") if part.strip()]


def _anchor(heading: str) -> str:
    slug = fold(heading)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def load_sections(root: Path | None = None) -> list[Section]:
    folder = root or _ROOT
    sections: list[Section] = []
    if not folder.is_dir():
        return sections
    for path in sorted(folder.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(raw)
        roles = set(_list_field(meta.get("roles", ""))) or {"operador"}
        screens = _list_field(meta.get("screens", ""))
        slug = path.stem.split("_", 1)[-1].replace("_", "-")
        title = meta.get("title") or slug
        current = "inicio"
        current_anchor = ""
        chunks: list[str] = []
        for line in body.splitlines():
            if line.startswith("## "):
                if chunks:
                    sections.append(
                        Section(slug, title, current, current_anchor, "\n".join(chunks).strip(), roles, screens)
                    )
                current = line[3:].strip()
                current_anchor = _anchor(current)
                chunks = []
            else:
                chunks.append(line)
        if chunks or not sections or sections[-1].slug != slug:
            sections.append(
                Section(slug, title, current, current_anchor, "\n".join(chunks).strip(), roles, screens)
            )
    return sections


class ManualIndex:
    def __init__(self, sections: list[Section] | None = None) -> None:
        self.sections = sections if sections is not None else load_sections()
        self._docs = [tokens(f"{s.title} {s.heading} {s.body}") for s in self.sections]
        self._df: dict[str, int] = {}
        for doc in self._docs:
            for term in set(doc):
                self._df[term] = self._df.get(term, 0) + 1
        self._avg = (sum(len(doc) for doc in self._docs) / len(self._docs)) if self._docs else 1.0

    def search(self, question: str, *, role: str, limit: int = 3) -> list[dict[str, str]]:
        query = tokens(question)
        if not query or not self.sections:
            return []
        k1 = 1.5
        b = 0.75
        n_docs = len(self.sections)
        scored: list[tuple[float, Section]] = []
        for index, section in enumerate(self.sections):
            if role != "admin" and role not in section.roles and "admin" not in section.roles:
                continue
            if role != "admin" and role not in section.roles:
                continue
            doc = self._docs[index]
            if not doc:
                continue
            counts: dict[str, int] = {}
            for term in doc:
                counts[term] = counts.get(term, 0) + 1
            score = 0.0
            for term in query:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                df = self._df.get(term, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1 - b + b * len(doc) / self._avg)
                score += idf * (tf * (k1 + 1)) / denom
            if score > 0:
                scored.append((score, section))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits = []
        for _score, section in scored[:limit]:
            text = section.body.strip().replace("\n", " ")
            if len(text) > 480:
                text = text[:477] + "…"
            hits.append(
                {
                    "titulo": section.title,
                    "seccion": section.heading,
                    "texto": text,
                    "url": section.url,
                }
            )
        return hits


_INDEX: ManualIndex | None = None


def get_index() -> ManualIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = ManualIndex()
    return _INDEX


def rebuild() -> ManualIndex:
    global _INDEX
    _INDEX = ManualIndex()
    return _INDEX


def search(question: str, *, role: str, limit: int = 3) -> list[dict[str, str]]:
    return get_index().search(question, role=role, limit=limit)


def all_screens() -> set[str]:
    screens: set[str] = set()
    for section in get_index().sections:
        screens.update(section.screens)
    return screens


def pages() -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for section in get_index().sections:
        seen.setdefault(section.slug, section.title)
    return [{"slug": slug, "title": title} for slug, title in seen.items()]
