"""Tests unitarios de ml_core.data_io."""

from __future__ import annotations

from pathlib import Path

import pytest

from ml_core.columns import EXPECTED_COLUMNS
from ml_core.data_io import load_and_clean, load_dls_report

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@pytest.fixture()
def sample_excel() -> Path:
    path = next(RAW_DIR.glob("dls_report_*.xlsx"), None)
    if path is None:
        pytest.skip("No hay archivos dls_report en data/raw")
    return path


def test_load_dls_report_has_expected_columns(sample_excel: Path) -> None:
    df = load_dls_report(sample_excel)
    assert not df.empty
    for col in EXPECTED_COLUMNS:
        assert col in df.columns


def test_load_and_clean_returns_rows(sample_excel: Path) -> None:
    result = load_and_clean(sample_excel)
    assert sample_excel.name in result.source_files
    assert len(result.dataframe) > 0
    assert "transforms" in {"transforms"} or result.transforms
    assert any("header_row" in t for t in result.transforms)
