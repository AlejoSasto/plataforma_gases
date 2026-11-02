from __future__ import annotations

from pathlib import Path

from app.modules.ingestion.pipeline.types import StageResult
from ml_core.columns import EXPECTED_COLUMNS
from ml_core.data_io import load_dls_report, load_processed_csv


def e1_extract(path: Path | str) -> StageResult:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = load_dls_report(p)
        kind = "dls_report"
    else:
        df = load_processed_csv(p)
        kind = "csv"
    df = df.copy()
    df["_source_file"] = p.name
    return StageResult(
        name="E1",
        dataframe=df,
        rows_in=int(len(df)),
        rows_out=int(len(df)),
        details={"kind": kind, "source": p.name, "expected_columns": EXPECTED_COLUMNS},
    )
