"""Cadena Alembic M1–M9 y semillas (Plan 16)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = ROOT / "migrations" / "versions"

CHAIN = [
    ("a1b2c3d4e5f6", None),
    ("b1c2d3e4f5a6", "a1b2c3d4e5f6"),
    ("b2c3d4e5f6a7", "b1c2d3e4f5a6"),
    ("b3c4d5e6f7a8", "b2c3d4e5f6a7"),
    ("b4c5d6e7f8a9", "b3c4d5e6f7a8"),
    ("b5c6d7e8f9a0", "b4c5d6e7f8a9"),
    ("b6c7d8e9f0a1", "b5c6d7e8f9a0"),
    ("b7c8d9e0f1a2", "b6c7d8e9f0a1"),
    ("b8c9d0e1f2a3", "b7c8d9e0f1a2"),
    ("b9d0e1f2a3b4", "b8c9d0e1f2a3"),
    ("c1d2e3f4a5b6", "b9d0e1f2a3b4"),
]


@pytest.mark.plan16
def test_alembic_chain_m1_m9() -> None:
    files = list(VERSIONS.glob("*.py"))
    by_rev: dict[str, Path] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("revision:"):
                rev = line.split("=", 1)[1].strip().strip('"').strip("'")
                by_rev[rev] = path
                break
    for rev, parent in CHAIN[1:]:
        assert rev in by_rev, f"falta revisión {rev}"
        text = by_rev[rev].read_text(encoding="utf-8")
        assert f'down_revision: Union[str, None] = "{parent}"' in text or f"down_revision = '{parent}'" in text
        assert "def upgrade()" in text
        assert "def downgrade()" in text
    drop = by_rev["b9d0e1f2a3b4"].read_text(encoding="utf-8")
    assert "op.drop_table(\"predictions\")" in drop
    assert "op.create_table(" in drop  # downgrade recrea


@pytest.mark.plan16
def test_seeds_idempotent_payload() -> None:
    from scripts.seed_catalog import seed_payloads

    a = seed_payloads()
    b = seed_payloads()
    assert a == b
    assert len(a["gas_types"]) == 6
    assert a["settings"]["forecast_horizons_min"] == [6, 12, 18]
    assert a["settings"]["grid_step_minutes"] == 6
    levels = {(t["gas_code"], t["level"]) for t in a["thresholds"]}
    assert ("CH4", "evacuar") in levels
    assert ("O2", "vigilar") in levels
