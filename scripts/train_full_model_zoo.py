"""Entrena el Model Zoo completo (tabular + DL) y promueve el mejor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.ml_training import service as ml_service
from app.modules.users.models import User
from ml_core.models.registry import DEFAULT_ALL


def main() -> int:
    mlruns = ROOT / "mlruns"
    mlruns.mkdir(exist_ok=True)
    tracking = f"file:{mlruns.as_posix()}"

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if admin is None:
            admin = db.query(User).filter(User.email == "ui.polish@example.com").first()
        if admin is None:
            print("ERROR: no hay usuario admin")
            return 1

        print(f"Train user={admin.email} algorithms={len(DEFAULT_ALL)}")
        result = ml_service.start_training(
            db,
            triggered_by=admin.id,
            dataset_version="gas_readings_full_zoo",
            scope="global",
            task="both",
            algorithms=list(DEFAULT_ALL),
            lookback_steps=20,
            horizon_minutes=7.5,
            params={
                "max_rows": 8000,
                "test_months": 3,
                "epochs": 5,
                "tracking_uri": tracking,
            },
        )
        print(
            f"OK job={result['job']['status']} "
            f"models={len(result['models'])} best={result['best_model_id']}"
        )
        for m in result["models"]:
            gates = (m.get("metrics") or {}).get("gates") or {}
            print(
                f"  - {m['algorithm']:20s} family={m.get('family')} "
                f"f1={((m.get('metrics') or {}).get('f1'))} "
                f"rmse={((m.get('metrics') or {}).get('rmse'))} "
                f"thesis={gates.get('meets_thesis')}"
            )

        best_id = result["best_model_id"]
        if best_id:
            promoted = ml_service.promote_model(db, best_id, actor_id=admin.id)
            print(f"Promoted #{promoted['id']} {promoted['algorithm']} → {promoted['status']}")
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
