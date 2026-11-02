"""Orquesta E1–E6. E5/E6 usan DB y G0; las etapas E1–E4 son puras."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.modules.ingestion.pipeline.e1_extract import e1_extract
from app.modules.ingestion.pipeline.e2_validate import e2_validate
from app.modules.ingestion.pipeline.e3_standardize import e3_standardize
from app.modules.ingestion.pipeline.e4_quality import e4_quality
from app.modules.ingestion.pipeline.e5_load import e5_load
from app.modules.ingestion.pipeline.e6_grid import e6_grid
from app.modules.ingestion.pipeline.types import StageResult


def run_stages_pure(path: Path | str) -> list[StageResult]:
    s1 = e1_extract(path)
    s2 = e2_validate(s1.dataframe)
    s3 = e3_standardize(s2.dataframe)
    s4 = e4_quality(s3.dataframe)
    return [s1, s2, s3, s4]


def run_pipeline(
    path: Path | str,
    *,
    db: Session | None = None,
    step_minutes: int = 1,
    persist: bool = False,
) -> dict[str, Any]:
    stages = run_stages_pure(path)
    result: dict[str, Any] = {
        "source": str(path),
        "stages": [
            {
                "name": s.name,
                "rows_in": s.rows_in,
                "rows_out": s.rows_out,
                "rows_rejected": s.rows_rejected,
                "details": s.details,
            }
            for s in stages
        ],
    }
    last = stages[-1]
    if persist and db is not None:
        s5 = e5_load(db, last.dataframe, source_path=path)
        stages.append(s5)
        result["stages"].append(
            {
                "name": s5.name,
                "rows_in": s5.rows_in,
                "rows_out": s5.rows_out,
                "rows_rejected": s5.rows_rejected,
                "details": s5.details,
            }
        )
    s6 = e6_grid(last.dataframe, step_minutes=step_minutes)
    result["stages"].append(
        {
            "name": s6.name,
            "rows_in": s6.rows_in,
            "rows_out": s6.rows_out,
            "rows_rejected": s6.rows_rejected,
            "details": s6.details,
        }
    )
    result["grid_rows"] = int(len(s6.dataframe))
    return result
