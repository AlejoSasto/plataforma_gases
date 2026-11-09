"""Reconstruye la plataforma desde los datos reales. Se detiene en el primer fallo.

  python scripts/build_real_platform.py --confirm
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = sys.executable
REPORT = ROOT / "reports" / "real_platform" / "build_report.md"


def _run(args: list[str]) -> None:
    code = subprocess.call(args, cwd=str(ROOT))
    if code != 0:
        raise RuntimeError(f"comando falló ({code}): {' '.join(args)}")


def build(*, confirm: bool, promote: bool) -> str:
    if not confirm:
        raise RuntimeError("falta --confirm")
    steps = [
        ("migraciones", [PY, "-m", "alembic", "upgrade", "head"]),
        ("semillas", [PY, "scripts/seed_catalog.py"]),
        ("superadmin", [PY, "scripts/create_superadmin.py"]),
        ("etl", [PY, "scripts/load_processed_dataset.py", "--consolidado"]),
        ("eventos", [PY, "scripts/rebuild_events.py", "--from-db", "--persist"]),
    ]
    done: list[str] = []
    for name, cmd in steps:
        try:
            _run(cmd)
        except Exception as exc:
            raise RuntimeError(f"paso {name}: {exc}") from exc
        done.append(name)
    from app.core.database import SessionLocal
    from app.modules.catalog.models import AppSetting
    from app.modules.sensors_ingestion.instruments import backfill_instruments
    from ml_core.diagnosis_g1 import render_g1_markdown, run_g1
    from scripts.diagnose_real_data import _load_from_db

    db = SessionLocal()
    try:
        backfill_instruments(db)
        db.commit()
        done.append("equipos")
        frame, _source = _load_from_db()
        report = run_g1(frame)
        out = ROOT / "reports" / "diagnostico"
        out.mkdir(parents=True, exist_ok=True)
        (out / "diagnostico_g1.json").write_text(
            __import__("json").dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        (out / "diagnostico_g1.md").write_text(render_g1_markdown(report), encoding="utf-8")
        for key, value in report["parameters"].items():
            row = db.get(AppSetting, key)
            if row is None:
                db.add(AppSetting(key=key, value=value))
            else:
                row.value = value
        db.commit()
        done.append("diagnostico")
        from ml_core.experiments.real_benchmark import run_real_benchmark
        from app.modules.forecasting.models import BacktestForecast, BenchmarkRun
        from app.modules.sensors_ingestion.models import Sensor

        work = frame.rename(columns={"tiempo_inicio": "ts", "leyendo": "value", "sensor_code": "sensor_code"})
        if "ts" not in work.columns:
            work["ts"] = work["tiempo_inicio"]
        if "value" not in work.columns:
            work["value"] = work["leyendo"]
        result = run_real_benchmark(
            work,
            model_keys=list(report["parameters"]["eligible_models"]),
        )
        run = BenchmarkRun(
            g1_params=report["parameters"],
            is_final_test=False,
            selection_report=result["report"],
            promoted_algorithm="persistencia",
            manifest={"available": result["available"], "unavailable": result["unavailable"]},
        )
        db.add(run)
        db.flush()
        sensors = {s.code: s.id for s in db.query(Sensor).all()}
        for row in result["rows"]:
            sid = sensors.get(row["sensor_code"])
            if sid is None:
                continue
            db.add(
                BacktestForecast(
                    run_id=run.id,
                    model_key=row["model"],
                    fold_index=row["fold_index"],
                    sensor_id=sid,
                    issued_at=row["issued_at"],
                    horizon_min=row["horizon_min"],
                    q10=row["q10"],
                    q50=row["q50"],
                    q90=row["q90"],
                    q95=row["q95"],
                    y_true=row["y_true"],
                    decided_level=row["decided_level"],
                    train_end=row["train_end"],
                )
            )
        db.commit()
        done.append(f"benchmark filas={len(result['rows'])} run={run.id}")
    except Exception as exc:
        raise RuntimeError(f"paso diagnostico/equipos: {exc}") from exc
    finally:
        db.close()

    lines = [
        "# Informe de reconstrucción",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Pasos completados:",
        "",
    ]
    for name in done:
        lines.append(f"- {name}")
    lines.append("")
    lines.append(f"Promoción pedida: {'sí' if promote else 'no'}.")
    lines.append("")
    text = "\n".join(lines)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    try:
        print(build(confirm=args.confirm, promote=args.promote))
    except Exception as exc:
        print(f"DETENIDO {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
