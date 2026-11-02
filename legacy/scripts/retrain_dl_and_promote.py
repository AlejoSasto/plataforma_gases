"""Reentrena solo DL y unifica production del Model Zoo."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.modules.ml_training import repository as repo
from app.modules.ml_training import service as ml_service
from app.modules.ml_training.models import ModelRegistry
from app.modules.users.models import User
from legacy.ml_core_models.registry import DEFAULT_SEQUENCE


def main() -> int:
    mlruns = ROOT / "mlruns"
    mlruns.mkdir(exist_ok=True)
    tracking = f"file:{mlruns.as_posix()}"
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").one()
        print("Retrain DL:", DEFAULT_SEQUENCE)
        result = ml_service.start_training(
            db,
            triggered_by=admin.id,
            dataset_version="gas_readings_dl",
            scope="global",
            task="both",
            algorithms=list(DEFAULT_SEQUENCE),
            lookback_steps=20,
            horizon_minutes=7.5,
            params={
                "max_rows": 12000,
                "test_months": 3,
                "epochs": 12,
                "tracking_uri": tracking,
            },
        )
        print("job", result["job"]["status"], "n", len(result["models"]), "best", result["best_model_id"])
        for m in result["models"]:
            met = m.get("metrics") or {}
            print(
                m["algorithm"],
                "f1=", met.get("f1"),
                "recall=", met.get("recall"),
                "rmse=", met.get("rmse"),
                "thesis=", (met.get("gates") or {}).get("meets_thesis"),
            )

        # Unificar: un solo production (mejor thesis tabular o best_id)
        for row in db.query(ModelRegistry).filter(ModelRegistry.status == "production").all():
            row.status = "archived"
            db.add(row)
        db.flush()

        # Preferir random_forest reciente que cumpla thesis
        best_tab = (
            db.query(ModelRegistry)
            .filter(ModelRegistry.algorithm == "random_forest")
            .order_by(ModelRegistry.id.desc())
            .first()
        )
        target_id = best_tab.id if best_tab else result["best_model_id"]
        promoted = ml_service.promote_model(db, target_id, actor_id=admin.id)
        print("production", promoted["id"], promoted["algorithm"])

        seq_n = (
            db.query(ModelRegistry)
            .filter(ModelRegistry.algorithm.in_(list(DEFAULT_SEQUENCE)))
            .count()
        )
        print("sequence models total", seq_n)
        return 0
    except Exception as exc:  # noqa: BLE001
        print("ERROR", type(exc).__name__, str(exc))
        import traceback

        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
