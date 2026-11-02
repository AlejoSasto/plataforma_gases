"""Ningún código de runtime referencia el módulo/tabla predictions (Plan 16 M9)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("app", "ml_core", "scripts", "tests")
SKIP_PARTS = {".pyc", "__pycache__"}
ALLOWED = (
    "predictions.view",
    "Ningún código de runtime referencia el módulo/tabla predictions",
)
FORBIDDEN = [
    re.compile(r"app\.modules\.predictions"),
    re.compile(r"class Prediction\b"),
    re.compile(r"/api/predictions"),
    re.compile(r"from app\.modules\.predictions"),
    re.compile(r"ForeignKey\([\"']predictions\.id"),
]


@pytest.mark.plan16
def test_no_predictions_module_in_runtime() -> None:
    hits: list[str] = []
    for folder in SCAN_DIRS:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".html"}:
                continue
            if path.name == "test_no_predictions_references.py":
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), start=1):
                if any(allow in line for allow in ALLOWED):
                    continue
                for pat in FORBIDDEN:
                    if pat.search(line):
                        hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert hits == [], "referencias prohibidas:\n" + "\n".join(hits)


@pytest.mark.plan16
def test_predictions_package_removed() -> None:
    assert not (ROOT / "app" / "modules" / "predictions" / "models.py").exists()
    assert not (ROOT / "app" / "modules" / "predictions" / "service.py").exists()
