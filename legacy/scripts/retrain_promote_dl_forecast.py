"""Reentrena LSTM/GRU/Transformer y promueve el mejor forecast (task=both)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.ml_training import service as ml_service
from app.modules.users.models import User

DL_ALGOS = ["lstm", "gru", "transformer"]
TARGET_RMSE = 0.05


def main() -> int:
    mlruns = ROOT / "mlruns"
    mlruns.mkdir(exist_ok=True)
    tracking = f"file:{mlruns.as_posix()}"

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if admin is None:
            admin = db.query(User).order_by(User.id.asc()).first()
        if admin is None:
            print("ERROR: no hay usuario")
            return 1

        print(f"Retrain DL user={admin.email} algos={DL_ALGOS}")
        result = ml_service.start_training(
            db,
            triggered_by=admin.id,
            dataset_version="gas_readings_dl_forecast",
            scope="global",
            task="both",
            algorithms=DL_ALGOS,
            lookback_steps=20,
            horizon_minutes=7.5,
            params={
                "max_rows": 12000,
                "test_months": 3,
                "epochs": 12,
                "tracking_uri": tracking,
            },
        )
        print(
            f"OK job={result['job']['status']} "
            f"models={len(result['models'])} best={result['best_model_id']}"
        )

        best_id = result["best_model_id"]
        best_row = None
        # Preferir menor RMSE entre modelos sequence (objetivo forecast thesis)
        by_rmse = []
        for m in result["models"]:
            metrics = m.get("metrics") or {}
            gates = metrics.get("gates") or {}
            rmse = metrics.get("rmse")
            print(
                f"  - {m['algorithm']:14s} id={m['id']} "
                f"rmse={rmse} f1={metrics.get('f1')} "
                f"recall={metrics.get('recall')} precision={metrics.get('precision')} "
                f"thesis={gates.get('meets_thesis')}"
            )
            if rmse is not None:
                by_rmse.append((float(rmse), m))
        if by_rmse:
            by_rmse.sort(key=lambda x: x[0])
            best_row = by_rmse[0][1]
            best_id = best_row["id"]
        elif best_id:
            best_row = next((m for m in result["models"] if m["id"] == best_id), None)

        if best_id:
            promoted = ml_service.promote_model(db, best_id, actor_id=admin.id)
            rmse = (best_row or {}).get("metrics", {}).get("rmse")
            note = (
                f"rmse={rmse} (target≤{TARGET_RMSE})"
                if rmse is not None
                else "sin rmse"
            )
            if rmse is not None and float(rmse) > TARGET_RMSE:
                print(
                    f"WARN: promovido #{promoted['id']} {promoted['algorithm']} "
                    f"pero {note} — umbral thesis no alcanzado en datos actuales"
                )
            else:
                print(f"Promoted #{promoted['id']} {promoted['algorithm']} {note}")
        else:
            print("WARN: no hay best_model_id para promover")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
