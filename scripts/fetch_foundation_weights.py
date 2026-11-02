"""Descarga pesos fundacionales en la construcción de la imagen (borde sin red).

No descarga nada si las librerías no están instaladas.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "storage" / "models" / "foundation"
DEST.mkdir(parents=True, exist_ok=True)


def main() -> int:
    tried = []
    for name in ("chronos", "timesfm"):
        try:
            __import__(name)
            tried.append(f"{name}: instalado (pesos según caché de HuggingFace)")
        except Exception as exc:  # noqa: BLE001
            tried.append(f"{name}: omitido ({exc.__class__.__name__})")
    (DEST / "README.txt").write_text(
        "Pesos fundacionales para operación sin red.\n" + "\n".join(tried),
        encoding="utf-8",
    )
    print("\n".join(tried))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
