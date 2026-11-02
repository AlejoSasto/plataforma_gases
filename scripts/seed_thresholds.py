"""Semilla de umbrales normativos (Plan 15 F4 / Plan 16).

Escribe JSON versionado y, si hay DB, upsert en normative_thresholds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.seed_catalog import main as seed_catalog_main
from ml_core.domain.thresholds import seed_as_records

OUT = ROOT / "reports" / "diagnostico" / "normative_thresholds_seed.json"


def main() -> int:
    records = seed_as_records()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return seed_catalog_main()


if __name__ == "__main__":
    raise SystemExit(main())
