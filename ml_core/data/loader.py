"""Carga de marcos de entrenamiento: solo datos reales (Plan 15 F1)."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
from sqlalchemy.orm import Session


class SyntheticDataError(ValueError):
    """Se intentó entrenar o evaluar con filas sintéticas."""


def load_training_frame(
    db: Session,
    *,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """Lee gas_readings reales. Lanza si aparece cualquier fila sintética."""
    from app.modules.sensors_ingestion.models import GasReading, Sensor

    q = (
        db.query(
            GasReading.id,
            GasReading.sensor_id,
            GasReading.leyendo,
            GasReading.unidad,
            GasReading.temperatura,
            GasReading.tiempo_inicio,
            GasReading.tiempo_fin,
            GasReading.is_synthetic,
            GasReading.source_file,
            Sensor.code.label("sensor_code"),
            Sensor.gas_type.label("gas"),
        )
        .join(Sensor, Sensor.id == GasReading.sensor_id)
    )
    if max_rows:
        q = q.order_by(GasReading.tiempo_inicio).limit(int(max_rows) * 2)
    rows = q.all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([r._mapping for r in rows])
    n_synth = int(df["is_synthetic"].astype(bool).sum())
    if n_synth:
        raise SyntheticDataError(
            f"El cargador de entrenamiento rechazó {n_synth} filas sintéticas"
        )
    df = df.loc[~df["is_synthetic"].astype(bool)].copy()
    if max_rows and len(df) > max_rows:
        df = df.head(max_rows)
    return df.reset_index(drop=True)


def assert_no_synthetic(frame: pd.DataFrame) -> None:
    if "is_synthetic" not in frame.columns:
        return
    n = int(frame["is_synthetic"].astype(bool).sum())
    if n:
        raise SyntheticDataError(f"Marco contiene {n} filas sintéticas")
