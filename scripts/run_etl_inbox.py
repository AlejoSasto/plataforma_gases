"""Procesa una vez la carpeta data/inbox.

Uso:
  python scripts/run_etl_inbox.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.sensors_ingestion.scheduler import process_inbox_once


def main() -> None:
    n = process_inbox_once()
    print(f"Archivos procesados: {n}")


if __name__ == "__main__":
    main()
