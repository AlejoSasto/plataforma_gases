"""Carga el CSV processed real a gas_readings.

Uso:
  python scripts/load_processed_dataset.py --consolidado
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.ingestion.pipeline.run import run_pipeline

PROCESSED = ROOT / "data" / "processed"
CONSOLIDADO = PROCESSED / "Procesamiento_de_Datos.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga el consolidado real a PostgreSQL")
    parser.add_argument("--consolidado", action="store_true", help="Carga CSV real")
    args = parser.parse_args()
    if not args.consolidado:
        parser.error("Indica --consolidado (el dataset 24m sintético se retiró, Plan 15 F1)")

    if not CONSOLIDADO.exists():
        raise SystemExit(f"No existe {CONSOLIDADO}")

    db = SessionLocal()
    try:
        result = run_pipeline(CONSOLIDADO, db=db, persist=True, step_minutes=1)
        print(json_summary(result))
    finally:
        db.close()


def json_summary(result: dict) -> str:
    import json

    return json.dumps(
        {s["name"]: {"in": s["rows_in"], "out": s["rows_out"], "rej": s["rows_rejected"]} for s in result["stages"]},
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
