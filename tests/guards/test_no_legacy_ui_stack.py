"""F7: sin Bootstrap, Chart.js, Inter ni theme.css en la interfaz."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCAN = [
    ROOT / "app" / "templates",
    ROOT / "app" / "static",
]
NEEDLES = (
    "bootstrap",
    "chart.js",
    "chart.umd",
    "family=Inter",
    "theme.css",
)


@pytest.mark.plan18
def test_no_bootstrap_chartjs_inter_theme() -> None:
    hits: list[str] = []
    for folder in SCAN:
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".html", ".css", ".js"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in NEEDLES:
                if needle.lower() in text.lower():
                    hits.append(f"{path.relative_to(ROOT)} → {needle}")
    assert hits == []
