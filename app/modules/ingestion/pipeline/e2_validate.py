from __future__ import annotations

import pandas as pd

from app.modules.ingestion.pipeline.types import StageResult
from ml_core.columns import COL_READING, EXPECTED_COLUMNS


def e2_validate(df: pd.DataFrame) -> StageResult:
    rows_in = int(len(df))
    rejected: list[dict] = []
    work = df.copy()
    for col in EXPECTED_COLUMNS:
        if col not in work.columns:
            work[col] = pd.NA
    work[COL_READING] = pd.to_numeric(work[COL_READING], errors="coerce")
    work["Tiempo de Inicio"] = pd.to_datetime(work["Tiempo de Inicio"], errors="coerce")
    if "Tiempo de finalización" in work.columns:
        work["Tiempo de finalización"] = pd.to_datetime(
            work["Tiempo de finalización"], errors="coerce"
        )

    bad_sensor = work["Sensor"].isna() | (work["Sensor"].astype(str).str.strip() == "")
    bad_val = work[COL_READING].isna()
    bad_time = work["Tiempo de Inicio"].isna()
    keep = ~(bad_sensor | bad_val | bad_time)
    for idx in work.index[~keep]:
        reasons = []
        if bool(bad_sensor.loc[idx]):
            reasons.append("sensor_missing")
        if bool(bad_val.loc[idx]):
            reasons.append("leyendo_invalid")
        if bool(bad_time.loc[idx]):
            reasons.append("tiempo_inicio_invalid")
        rejected.append({"row": int(idx) if str(idx).isdigit() else idx, "reason": ",".join(reasons)})
    out = work.loc[keep].copy()
    return StageResult(
        name="E2",
        dataframe=out,
        rows_in=rows_in,
        rows_out=int(len(out)),
        rows_rejected=int((~keep).sum()),
        details={"rejected_sample": rejected[:50], "rejected_total": len(rejected)},
    )
