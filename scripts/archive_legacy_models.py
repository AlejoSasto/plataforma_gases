"""Archiva modelos en production que no pertenecen al zoo final.

  python scripts/archive_legacy_models.py --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_core.domain.g1 import FINAL_ZOO, OPTIONAL_ZOO

ALLOWED = set(FINAL_ZOO) | set(OPTIONAL_ZOO)


def is_legacy_production(algorithm: str, status: str) -> bool:
    return status == "production" and algorithm not in ALLOWED


def archive(db, *, confirm: bool) -> list[str]:
    from app.modules.ml_training.models import ModelRegistry

    rows = db.query(ModelRegistry).filter(ModelRegistry.status == "production").all()
    archived: list[str] = []
    for row in rows:
        if not is_legacy_production(row.algorithm, row.status):
            continue
        archived.append(row.algorithm)
        if confirm:
            row.status = "archived"
    if confirm:
        db.commit()
    return archived


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if not args.confirm:
        print("Falta --confirm. No se archivó nada.")
        return 1
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        names = archive(db, confirm=True)
    finally:
        db.close()
    print(f"OK archivados={names or 'ninguno'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
