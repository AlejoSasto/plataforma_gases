"""EDA mínimo para OE1 a partir del diagnóstico (Plan 15 F6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DIAG = ROOT / "reports" / "diagnostico" / "diagnostico_datos.json"
OUT = ROOT / "reports" / "eda" / "resumen.md"


def main() -> int:
    if not DIAG.exists():
        raise SystemExit("Falta diagnostico_datos.json. Corre scripts/diagnose_real_data.py")
    report = json.loads(DIAG.read_text(encoding="utf-8"))
    lines = [
        "# Exploración de datos reales (OE1)",
        "",
        "Generado desde el diagnóstico F0. Figuras interactivas viven en la pantalla de calidad (Plan 18).",
        "",
        f"- Filas: {report['n_rows']}",
        f"- Sensores: {report['n_sensors']}",
        f"- Gases: {', '.join(report['gases'])}",
        f"- Rango: {report['t_min']} → {report['t_max']}",
        f"- G0: banda `{report['g0']['band']}`, horizontes {report['g0']['horizons_min']}",
        "",
        "## Episodios (inicios)",
        "",
    ]
    for ep in report["episodes"]:
        lines.append(
            f"- {ep['gas']} {ep['level']}: {ep['onsets']} inicios → política `{ep['policy']}`"
        )
    lines += ["", "Los notebooks de `notebooks/` quedan como histórico; esta es la evidencia reproducible.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
