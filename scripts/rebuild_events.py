"""Reconstruye threshold_events. Dos corridas deben coincidir.

  python scripts/rebuild_events.py
  python scripts/rebuild_events.py --persist
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from app.modules.ingestion.rebuild import frame_signature, rebuild_events_frame, rebuild_grid_frame
from scripts.rebuild_grid import _from_csv


def persist_events(events: pd.DataFrame) -> int:
    from app.core.database import SessionLocal
    from app.modules.catalog.models import NormativeThreshold
    from app.modules.sensors_ingestion.models import Sensor, ThresholdEvent

    db = SessionLocal()
    try:
        sensors = {(s.code, s.gas_type): s.id for s in db.query(Sensor).all()}
        thresholds = {
            (t.gas_code, t.level): t.id for t in db.query(NormativeThreshold).all()
        }
        db.query(ThresholdEvent).filter(ThresholdEvent.detected_by == "etl").delete()
        n = 0
        for row in events.itertuples(index=False):
            sid = sensors.get((str(row.sensor_code), str(row.gas_code)))
            if sid is None:
                continue
            db.add(
                ThresholdEvent(
                    sensor_id=sid,
                    gas_code=str(row.gas_code),
                    level=str(row.level),
                    threshold_id=thresholds.get((str(row.gas_code), str(row.level))),
                    started_at=row.started_at,
                    ended_at=None if pd.isna(row.ended_at) else row.ended_at,
                    peak_value=None if pd.isna(row.peak_value) else float(row.peak_value),
                    peak_at=None if pd.isna(row.peak_at) else row.peak_at,
                    detected_by="etl",
                )
            )
            n += 1
        db.commit()
        return n
    finally:
        db.close()


def _from_db() -> pd.DataFrame:
    from app.core.database import SessionLocal
    from app.modules.sensors_ingestion.models import GasReading, Sensor

    db = SessionLocal()
    try:
        rows = (
            db.query(
                Sensor.code.label("sensor_code"),
                Sensor.gas_type.label("gas"),
                GasReading.tiempo_inicio.label("ts"),
                GasReading.value_canonical.label("value"),
            )
            .join(Sensor, Sensor.id == GasReading.sensor_id)
            .filter(GasReading.is_synthetic.is_(False))
            .all()
        )
    finally:
        db.close()
    return pd.DataFrame([r._mapping for r in rows])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "processed" / "Procesamiento_de_Datos.csv"),
    )
    parser.add_argument("--step", type=int, default=6)
    parser.add_argument("--from-db", action="store_true", help="Usa gas_readings canónicas")
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()
    if args.from_db:
        grid = _from_db()
        grid["value"] = pd.to_numeric(grid["value"], errors="coerce")
        grid = grid.dropna(subset=["value", "ts"])
    else:
        path = Path(args.input)
        if not path.exists():
            print(f"SKIP no hay {path}")
            return 0
        df = _from_csv(path)
        grid = rebuild_grid_frame(df, step_minutes=args.step)
    first = rebuild_events_frame(grid)
    second = rebuild_events_frame(grid)
    assert frame_signature(first) == frame_signature(second), "episodios no reproducibles"
    print(f"OK events rows={len(first)}")
    if args.persist:
        n = persist_events(first)
        print(f"OK persist {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
