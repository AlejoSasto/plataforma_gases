"""Utilidades para marcar filas sintéticas del dataset 24m."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_augmentation_manifest(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def mark_synthetic_from_manifest(
    df: pd.DataFrame,
    real_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Marca is_synthetic=True en filas del CSV 24m que no existen en el consolidado real.
    """
    out = df.copy()
    if real_df is None or real_df.empty:
        out["is_synthetic"] = False
        return out

    key_cols = ["Sensor", "Descripción", "Tiempo de Inicio", "Leyendo"]
    for col in key_cols:
        if col not in out.columns or col not in real_df.columns:
            out["is_synthetic"] = False
            return out

    left = out[key_cols].copy()
    for col in key_cols:
        left[col] = left[col].astype(str)
    right = real_df[key_cols].copy()
    for col in key_cols:
        right[col] = right[col].astype(str)
    right = right.drop_duplicates()

    merged = left.merge(right, on=key_cols, how="left", indicator=True)
    out["is_synthetic"] = merged["_merge"].to_numpy() == "left_only"
    return out


def manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    blocks = manifest.get("synthetic_blocks") or []
    return {
        "meta": manifest.get("meta") or {},
        "n_synthetic_blocks": len(blocks),
        "total_synthetic_rows_declared": sum(int(b.get("n_filas", 0)) for b in blocks),
    }
