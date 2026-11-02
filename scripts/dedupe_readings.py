"""Limpieza única de duplicados (sensor_id, tiempo_inicio) antes del UNIQUE del Plan 16."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.core.database import SessionLocal


SQL = """
DELETE FROM gas_readings a
USING gas_readings b
WHERE a.sensor_id = b.sensor_id
  AND a.tiempo_inicio = b.tiempo_inicio
  AND a.id > b.id
"""


def main() -> int:
    db = SessionLocal()
    try:
        result = db.execute(text(SQL))
        db.commit()
        print(f"Duplicados eliminados: {result.rowcount}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
