"""Plan 24 F1: sin textos del kit demo en templates/copy; mockups no se sirven."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BLACKLIST = [
    "Frente 3 Sur",
    "Frente 3",
    "Ana Rojas",
    "Carlos Pinzón",
    "Carlos Pinzon",
    "0,72",
    "Mina caso de estudio",
]

pytestmark = [pytest.mark.plan24, pytest.mark.plan]


def test_no_demo_strings_in_templates() -> None:
    offenders: list[str] = []
    paths = list((ROOT / "app" / "templates").rglob("*.html"))
    paths.append(ROOT / "app" / "shared" / "copy.py")
    for path in paths:
        body = path.read_text(encoding="utf-8", errors="replace")
        for needle in BLACKLIST:
            if needle in body:
                offenders.append(f"{path.relative_to(ROOT)} → {needle!r}")
    assert not offenders, "textos demo:\n" + "\n".join(offenders)


def test_app_does_not_serve_mockups() -> None:
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "mockups" not in main.lower()
    assert "vigia-design-kit" not in main
    # El kit no vive bajo static
    assert not (ROOT / "app" / "static" / "mockups").exists()
    assert not (ROOT / "app" / "static" / "vigia-design-kit").exists()
