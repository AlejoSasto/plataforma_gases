"""Reconstruye reading_grid. Dos corridas deben coincidir.

  python scripts/rebuild_grid.py
  python scripts/rebuild_grid.py --persist
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from app.modules.ingestion.rebuild import frame_signature, rebuild_grid_frame


def _from_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    rename = {}
    if "sensor_code" not in df.columns and "Sensor" in df.columns:
        rename["Sensor"] = "sensor_code"
    if "gas" not in df.columns and "Tipo de Gas" in df.columns:
        rename["Tipo de Gas"] = "gas"
    elif "gas" not in df.columns and "Gas" in df.columns:
        rename["Gas"] = "gas"
    if "value_canonical" not in df.columns and "Leyendo" in df.columns:
        rename["Leyendo"] = "value_canonical"
    if rename:
        df = df.rename(columns=rename)
    from app.shared.gas_catalog import canonicalize_gas_type, normalize_sensor_code

    if "sensor_code" in df.columns:
        df["sensor_code"] = df["sensor_code"].map(normalize_sensor_code)
    if "gas" in df.columns:
        df["gas"] = df["gas"].map(canonicalize_gas_type)
    return df


def persist_grid(grid: pd.DataFrame) -> int:
    from app.core.database import SessionLocal
    from app.modules.sensors_ingestion.models import ReadingGrid, Sensor

    db = SessionLocal()
    try:
        sensors = {(s.code, s.gas_type): s.id for s in db.query(Sensor).all()}
        n = 0
        for row in grid.itertuples(index=False):
            sid = sensors.get((str(row.sensor_code), str(row.gas)))
            if sid is None:
                continue
            existing = db.get(ReadingGrid, {"sensor_id": sid, "ts": row.ts})
            payload = {
                "value": None if pd.isna(row.value) else float(row.value),
                "is_imputed": bool(row.is_imputed),
                "is_missing": bool(row.is_missing),
            }
            if existing is None:
                db.add(ReadingGrid(sensor_id=sid, ts=row.ts, **payload))
            else:
                for k, v in payload.items():
                    setattr(existing, k, v)
            n += 1
        db.commit()
        return n
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "processed" / "Procesamiento_de_Datos.csv"),
    )
    parser.add_argument("--step", type=int, default=6)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    path = Path(args.input)
    if not path.exists():
        print(f"SKIP no hay {path}")
        return 0
    df = _from_csv(path)
    first = rebuild_grid_frame(df, step_minutes=args.step)
    second = rebuild_grid_frame(df, step_minutes=args.step)
    assert frame_signature(first) == frame_signature(second), "rejilla no reproducible"
    print(f"OK grid rows={len(first)} signature={frame_signature(first)[0]}")
    if args.persist:
        n = persist_grid(first)
        print(f"OK persist {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
