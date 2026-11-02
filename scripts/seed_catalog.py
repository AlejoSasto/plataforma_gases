"""Semillas idempotentes de catálogo (Plan 16).

  python scripts/seed_catalog.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.catalog.seed import GAS_TYPE_SEED, SETTINGS_SEED
from ml_core.domain.thresholds import seed_as_records

OUT = ROOT / "reports" / "diagnostico" / "normative_thresholds_seed.json"


def seed_payloads() -> dict[str, object]:
    return {
        "gas_types": [dict(r) for r in GAS_TYPE_SEED],
        "thresholds": seed_as_records(),
        "settings": dict(SETTINGS_SEED),
    }


def main() -> int:
    payload = seed_payloads()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload["thresholds"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        from app.modules.roles_permissions import models as _roles_models  # noqa: F401
        from app.modules.users import models as _users_models  # noqa: F401

        from app.core.database import SessionLocal
        from app.modules.catalog.seed import seed_catalog

        db = SessionLocal()
        try:
            counts = seed_catalog(db)
            print(f"OK catalog db {counts}")
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        print(f"WARN catálogo en JSON ({OUT}); DB no disponible: {exc}")
    print(f"OK {OUT} ({len(payload['thresholds'])} umbrales)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
