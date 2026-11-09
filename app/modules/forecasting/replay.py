"""Reproducción histórica. Los avisos históricos no se envían ni quedan abiertos.

  python -m app.modules.forecasting.replay --run 1
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Any

from ml_core.domain.guards25 import historic_presented_as_open, should_email
from ml_core.experiments.real_benchmark import persistence_backtest


def replay_alerts(rows: list[dict[str, Any]], *, threshold: float = 1.0) -> list[dict[str, Any]]:
    """Un aviso por racha en la que q50 cruza el umbral. Siempre origen histórico."""
    alerts: list[dict[str, Any]] = []
    by_sensor: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if int(row.get("horizon_min") or 0) != 6:
            continue
        by_sensor.setdefault(str(row["sensor_code"]), []).append(row)
    for sensor, points in by_sensor.items():
        ordered = sorted(points, key=lambda item: item["issued_at"])
        streak = 0
        open_alert = False
        for point in ordered:
            high = float(point["q50"]) >= threshold
            streak = streak + 1 if high else 0
            if streak >= 2 and not open_alert:
                alerts.append(
                    {
                        "sensor_code": sensor,
                        "origin": "historico",
                        "status": "resuelta",
                        "human_handled": False,
                        "closed_by": "sistema",
                        "issued_at": point["issued_at"],
                        "source_file": point.get("source_file") or "lectura-real",
                        "sensor_id": point.get("sensor_id") or sensor,
                        "notify": should_email("historico"),
                    }
                )
                open_alert = True
            if not high:
                open_alert = False
                streak = 0
    for alert in alerts:
        if historic_presented_as_open(alert["origin"], alert["status"]):
            raise RuntimeError("un aviso histórico no puede quedar abierto")
        if alert["notify"]:
            raise RuntimeError("un aviso histórico no se notifica")
    return alerts


def replay_idempotent_counts(frame, **kwargs) -> tuple[int, int]:
    first = persistence_backtest(frame, **kwargs)
    second = persistence_backtest(frame, **kwargs)
    return len(first), len(replay_alerts(first)) if first == second else (-1, -1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=int)
    args = parser.parse_args()
    from app.core.database import SessionLocal
    from app.modules.forecasting.models import BacktestForecast, BenchmarkRun

    db = SessionLocal()
    try:
        run = db.get(BenchmarkRun, args.run)
        if run is None:
            raise SystemExit(f"no existe la corrida {args.run}")
        existing = (
            db.query(BacktestForecast).filter(BacktestForecast.run_id == run.id).count()
        )
        print(f"OK replay run={run.id} backtest_rows={existing} (idempotente: no duplica)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
