"""Núcleo ML / ETL. El zoo tabular viejo vive en `legacy/` (Plan 23 F5)."""

from ml_core.columns import EXPECTED_COLUMNS
from ml_core.data_io import CleanResult, load_and_clean, load_dls_report, load_processed_csv
from ml_core.forecasting.adapters import ADAPTERS
from ml_core.forecasting.problem import ProblemSpec

__all__ = [
    "ADAPTERS",
    "EXPECTED_COLUMNS",
    "CleanResult",
    "ProblemSpec",
    "load_and_clean",
    "load_dls_report",
    "load_processed_csv",
]
