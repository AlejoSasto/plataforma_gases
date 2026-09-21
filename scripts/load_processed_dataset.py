"""Carga CSV processed (consolidado y/o 24m) a gas_readings.

Uso:
  python scripts/load_processed_dataset.py --consolidado
  python scripts/load_processed_dataset.py --augmented-24m
  python scripts/load_processed_dataset.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.sensors_ingestion import service as ingestion_service

PROCESSED = ROOT / "data" / "processed"
CONSOLIDADO = PROCESSED / "Procesamiento_de_Datos.csv"
AUGMENTED = PROCESSED / "Procesamiento_de_Datos_24m.csv"
MANIFEST = PROCESSED / "augmentation_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga datasets processed a PostgreSQL")
    parser.add_argument("--consolidado", action="store_true", help="Carga CSV real")
    parser.add_argument(
        "--augmented-24m",
        action="store_true",
        help="Carga CSV 24m marcando sintéticos vs consolidado",
    )
    parser.add_argument("--all", action="store_true", help="Carga consolidado + 24m")
    args = parser.parse_args()

    if not (args.consolidado or args.augmented_24m or args.all):
        parser.error("Indica --consolidado, --augmented-24m o --all")

    db = SessionLocal()
    try:
        if args.consolidado or args.all:
            if not CONSOLIDADO.exists():
                raise SystemExit(f"No existe {CONSOLIDADO}")
            run = ingestion_service.ingest_csv_paths(
                db,
                [CONSOLIDADO],
                is_synthetic=False,
            )
            print(
                f"Consolidado run_id={run.id} status={run.status} "
                f"ingested={run.rows_ingested} rejected={run.rows_rejected}"
            )

        if args.augmented_24m or args.all:
            if not AUGMENTED.exists():
                raise SystemExit(f"No existe {AUGMENTED}")
            run = ingestion_service.ingest_csv_paths(
                db,
                [AUGMENTED],
                is_synthetic=True,
                mark_against_real=CONSOLIDADO if CONSOLIDADO.exists() else None,
                manifest_path=MANIFEST if MANIFEST.exists() else None,
            )
            print(
                f"24m run_id={run.id} status={run.status} "
                f"ingested={run.rows_ingested} rejected={run.rows_rejected}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
