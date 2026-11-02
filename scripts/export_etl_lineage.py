"""Exporta linaje ETL v2 (evidencia OE2)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.ingestion.pipeline.run import run_pipeline

OUT = ROOT / "docs" / "etl" / "transformaciones.md"
SAMPLE = ROOT / "data" / "processed" / "Procesamiento_de_Datos.csv"


def main() -> int:
    if not SAMPLE.exists():
        raise SystemExit(f"No existe {SAMPLE}")
    result = run_pipeline(SAMPLE, persist=False, step_minutes=1)
    lines = [
        "# Transformaciones ETL v2",
        "",
        "Contrato de etapas E1–E6 (Plan 15 F2). Conteos de la última corrida sobre el consolidado real (sin persistir).",
        "",
        f"Fuente: `{Path(result['source']).name}`",
        "",
        "| Etapa | Filas in | Filas out | Rechazadas | Detalle |",
        "|-------|--------:|---------:|-----------:|---------|",
    ]
    for s in result["stages"]:
        detail = json.dumps(s["details"], ensure_ascii=False, default=str)
        if len(detail) > 180:
            detail = detail[:177] + "..."
        lines.append(
            f"| {s['name']} | {s['rows_in']} | {s['rows_out']} | {s['rows_rejected']} | `{detail}` |"
        )
    lines += [
        "",
        "## Etapas",
        "",
        "- **E1 Extraer:** Excel `dls_report` (hoja Resumen, cabecera 24) o CSV consolidado.",
        "- **E2 Validar:** 15 columnas canónicas, `Leyendo` numérico, fechas parseables.",
        "- **E3 Estandarizar:** gas/sensor canónicos; CH₄ %LEL → % vol (LIE=5,0); CO₂ %vol → ppm.",
        "- **E4 Calidad:** marca problemas; no borra (salvo exclusión de fuera de rango / unidad desconocida al cargar).",
        "- **E5 Cargar:** idempotente por SHA-256 del archivo y (sensor, tiempo).",
        "- **E6 Rejilla:** remuestreo regular; ffill ≤ 3 pasos; huecos largos como faltantes. Nunca interpola al futuro.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    (OUT.parent / "ultima_corrida.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"OK {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
