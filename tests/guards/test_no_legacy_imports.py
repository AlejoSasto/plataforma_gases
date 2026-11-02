"""Plan 23 F5: app/ y ml_core/forecasting no importan legacy."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCOPES = [ROOT / "app", ROOT / "ml_core" / "forecasting"]

pytestmark = [pytest.mark.plan23, pytest.mark.plan]


def _imports_of(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_no_legacy_imports() -> None:
    offenders: list[str] = []
    for scope in SCOPES:
        for path in scope.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            for name in _imports_of(path):
                if name == "legacy" or name.startswith("legacy."):
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
                if name.startswith("ml_core.models") or name.startswith("ml_core.features.build_features"):
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
                if name in {"ml_core.features.targets", "ml_core.features.sequences"}:
                    offenders.append(f"{path.relative_to(ROOT)} → {name}")
    assert not offenders, "imports prohibidos:\n" + "\n".join(offenders)


def test_no_probability_risk_thresholds() -> None:
    from app.core import config

    settings = config.get_settings()
    for attr in (
        "risk_threshold_precaution",
        "risk_threshold_alert",
        "risk_threshold_critical",
        "thesis_recall_min",
        "ml_lead_minutes_min",
        "ml_lead_minutes_max",
    ):
        assert not hasattr(settings, attr), f"settings aún expone {attr}"

    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for needle in ("RISK_THRESHOLD_", "THESIS_RECALL_MIN", "ML_LEAD_MINUTES_"):
        assert needle not in example, f".env.example aún tiene {needle}"

    rec = (ROOT / "app" / "modules" / "alerts" / "recommendations.py").read_text(encoding="utf-8")
    assert "probability_to_risk_level" not in rec
    assert "risk_threshold" not in rec
