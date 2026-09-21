"""Núcleo ML / ETL — lectura, features y entrenamiento (Planes 03–04)."""

from ml_core.augmentation import load_augmentation_manifest, mark_synthetic_from_manifest
from ml_core.columns import EXPECTED_COLUMNS
from ml_core.data_io import CleanResult, load_and_clean, load_dls_report, load_processed_csv
from ml_core.features.build_features import build_features
from ml_core.models.train_model import train

__all__ = [
    "EXPECTED_COLUMNS",
    "CleanResult",
    "load_and_clean",
    "load_dls_report",
    "load_processed_csv",
    "load_augmentation_manifest",
    "mark_synthetic_from_manifest",
    "build_features",
    "train",
]
