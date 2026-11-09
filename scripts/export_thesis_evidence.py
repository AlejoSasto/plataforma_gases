"""Exporta evidencia de una corrida desde la base. Ninguna cifra se escribe a mano.

  python scripts/export_thesis_evidence.py --run 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def export_run(db, run_id: int, dest: Path) -> Path:
    from app.modules.forecasting.models import BacktestForecast, BenchmarkRun

    run = db.get(BenchmarkRun, run_id)
    if run is None:
        raise RuntimeError(f"no existe la corrida {run_id}")
    dest.mkdir(parents=True, exist_ok=True)
    rows = db.query(BacktestForecast).filter(BacktestForecast.run_id == run_id).all()
    payload = {
        "run_id": run.id,
        "commit": run.commit_sha,
        "data_hash": run.data_hash,
        "is_final_test": run.is_final_test,
        "n_forecasts": len(rows),
        "selection_report": run.selection_report,
    }
    (dest / "run_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = ["modelo,horizonte,q50,y_true", ""]
    # header without the blank I just added — rewrite cleanly
    lines = ["modelo,horizonte,q50,y_true"]
    for row in rows:
        lines.append(f"{row.model_key},{row.horizon_min},{row.q50},{row.y_true}")
    (dest / "backtest.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dest / "seleccion.md").write_text(run.selection_report or "Sin informe.\n", encoding="utf-8")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, required=True)
    args = parser.parse_args()
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        dest = export_run(db, args.run, ROOT / "reports" / "thesis")
    finally:
        db.close()
    print(f"OK {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
