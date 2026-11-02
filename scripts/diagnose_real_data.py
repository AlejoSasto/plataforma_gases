"""Diagnóstico de datos reales (Plan 15 F0). Solo lectura. Idempotente.

Uso:
  python scripts/diagnose_real_data.py
  python scripts/diagnose_real_data.py --from-csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from ml_core.diagnosis import run_diagnosis
from ml_core.data_io import load_processed_csv

OUT_DIR = ROOT / "reports" / "diagnostico"
CONSOLIDADO = ROOT / "data" / "processed" / "Procesamiento_de_Datos.csv"


def _load_from_db() -> tuple[pd.DataFrame, str]:
    from app.core.database import SessionLocal
    from app.modules.sensors_ingestion.models import GasReading, Sensor

    db = SessionLocal()
    try:
        rows = (
            db.query(
                GasReading.leyendo,
                GasReading.unidad,
                GasReading.tiempo_inicio,
                GasReading.tiempo_fin,
                GasReading.is_synthetic,
                GasReading.source_file,
                Sensor.code.label("sensor_code"),
                Sensor.gas_type.label("gas"),
            )
            .join(Sensor, Sensor.id == GasReading.sensor_id)
            .filter(GasReading.is_synthetic.is_(False))
            .all()
        )
    finally:
        db.close()
    if not rows:
        raise RuntimeError("gas_readings reales vacío")
    df = pd.DataFrame([r._mapping for r in rows])
    return df, "postgresql.gas_readings[is_synthetic=false]"


def _load_from_csv() -> tuple[pd.DataFrame, str]:
    if not CONSOLIDADO.exists():
        raise SystemExit(f"No existe {CONSOLIDADO}")
    df = load_processed_csv(CONSOLIDADO)
    return df, f"csv:{CONSOLIDADO.name}"


def render_markdown(report: dict) -> str:
    g0 = report["g0"]
    lines = [
        "# Diagnóstico de datos reales",
        "",
        f"Generado: `{report['generated_at']}`",
        f"Fuente: `{report['source']}`",
        "",
        "## Resumen",
        "",
        f"- Filas reales: **{report['n_rows']}**",
        f"- Pares sensor-gas: **{report['n_sensors']}**",
        f"- Gases: {', '.join(report['gases'])}",
        f"- Rango: {report['t_min']} → {report['t_max']}",
        f"- Duplicados exactos: {report['duplicates']['exact']}",
        f"- Casi duplicados (≤60 s, mismo valor): {report['duplicates']['near_same_value_within_60s']}",
        "",
        "## Compuerta G0",
        "",
        f"- Δt mediana (máximo entre CH₄, CO, H₂S): **{g0['dt_p50_min_priority_max']} min**",
        f"- Banda: `{g0['band']}`",
        f"- Horizontes (minutos): `{g0['horizons_min']}`",
        f"- {g0['note']}",
        "",
        "Δt por gas prioritario:",
        "",
        "| Gas | Δt p50 (min) |",
        "|-----|-------------:|",
    ]
    for gas, val in (g0.get("dt_p50_min_by_gas") or {}).items():
        lines.append(f"| {gas} | {val if val is not None else '—'} |")
    lines += [
        "",
        "Umbrales usados para episodios: semilla Plan 15 F4 (`verified=false`).",
        f"LIE CH₄ usado en conversión %LEL→%vol: {report['lel_ch4_percent_vol']} % vol.",
        "",
        "## Episodios de inicio por gas y nivel",
        "",
        "| Gas | Nivel | Dirección | Umbral | Inicios | Política de evaluación |",
        "|-----|-------|-----------|-------:|--------:|------------------------|",
    ]
    for ep in report["episodes"]:
        lines.append(
            f"| {ep['gas']} | {ep['level']} | {ep['direction']} | {ep['threshold']} | "
            f"{ep['onsets']} | {ep['policy']} |"
        )
    lines += [
        "",
        "## Densidad por mes y gas",
        "",
        "| Mes | Gas | Filas |",
        "|-----|-----|------:|",
    ]
    for row in sorted(report["density_month_gas"], key=lambda r: (r["month"], r["gas"])):
        lines.append(f"| {row['month']} | {row['gas']} | {row['n']} |")
    lines += [
        "",
        "## Unidades observadas",
        "",
    ]
    for gas, units in sorted(report["units_by_gas"].items()):
        lines.append(f"- **{gas}**: {', '.join(units) if units else '—'}")
    lines += [
        "",
        "## Sensores (intervalo y tipo probable)",
        "",
        "| Sensor | Gas | n | p10 | p50 | p90 | % huecos >3×med | Tipo |",
        "|--------|-----|--:|----:|----:|----:|----------------:|------|",
    ]
    for s in report["sensors"]:
        lines.append(
            f"| `{s['sensor_code']}` | {s['gas']} | {s['n']} | {s['dt_p10_min']} | "
            f"{s['dt_p50_min']} | {s['dt_p90_min']} | {s['gap_gt_3median_pct']} | {s['kind']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico de datos reales")
    parser.add_argument("--from-csv", action="store_true", help="Forzar CSV consolidado")
    args = parser.parse_args()

    source_note = ""
    if args.from_csv:
        df, source_note = _load_from_csv()
    else:
        try:
            df, source_note = _load_from_db()
        except Exception as exc:
            print(f"DB no disponible ({exc}); se usa el consolidado CSV.", file=sys.stderr)
            df, source_note = _load_from_csv()

    report = run_diagnosis(df, source=source_note)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "diagnostico_datos.json"
    md_path = OUT_DIR / "diagnostico_datos.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (OUT_DIR / "g0_decision.json").write_text(
        json.dumps(report["g0"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK {md_path}")
    print(f"OK {json_path}")
    print(f"G0 band={report['g0']['band']} horizons={report['g0']['horizons_min']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
