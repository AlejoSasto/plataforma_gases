"""Verifica conectividad a PostgreSQL: SELECT 1."""

import sys
from pathlib import Path

# Permite ejecutar el script desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.database import engine


def main() -> int:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            value = result.scalar()
        print(f"OK: conexión a la base confirmada (SELECT 1 -> {value})")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: no se pudo conectar a la base: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
