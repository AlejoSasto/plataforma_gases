"""Elimina filas sintéticas de gas_readings (Plan 15 F1).

  python scripts/purge_synthetic.py          # dry-run
  python scripts/purge_synthetic.py --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func

from app.core.database import SessionLocal
from app.modules.audit.service import record_audit
from app.modules.sensors_ingestion.models import GasReading


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Ejecuta el borrado")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        n = db.query(func.count(GasReading.id)).filter(GasReading.is_synthetic.is_(True)).scalar() or 0
        print(f"Filas sintéticas: {n}")
        if not args.confirm:
            print("Dry-run. Pasa --confirm para borrar.")
            return 0
        deleted = db.query(GasReading).filter(GasReading.is_synthetic.is_(True)).delete(
            synchronize_session=False
        )
        record_audit(
            db,
            action="data.purge_synthetic",
            user_id=None,
            resource_type="gas_readings",
            resource_id=None,
            metadata={"deleted": int(deleted)},
        )
        db.commit()
        print(f"Borradas: {deleted}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
