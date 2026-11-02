from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.plan(15)

FORBIDDEN = (
    "KFold",
    "StratifiedKFold",
    "train_test_split",
)

ROOT = Path(__file__).resolve().parents[2] / "ml_core"


def test_no_shuffle_splitters() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                if token == "train_test_split" and "shuffle=False" in text:
                    continue
                offenders.append(f"{path.relative_to(ROOT.parent)}:{token}")
    assert offenders == []
