"""Carga y limpieza de archivos dls_report (portado desde notebooks)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from ml_core.columns import (
    COL_READING,
    COLUMN_RENAMES,
    DLS_HEADER_ROW,
    DLS_SHEET_NAME,
    EXPECTED_COLUMNS,
)


@dataclass
class CleanResult:
    """Resultado de limpieza listo para persistir."""

    dataframe: pd.DataFrame
    rejected: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    transforms: list[str] = field(default_factory=list)


def load_dls_report(path: Path | str) -> pd.DataFrame:
    """
    Carga un archivo dls_report_*.xlsx y devuelve un DataFrame normalizado
    con el esquema de Procesamiento de Datos.
    """
    ruta = Path(path)
    df = pd.read_excel(ruta, sheet_name=DLS_SHEET_NAME, header=DLS_HEADER_ROW)

    col_desc = [c for c in df.columns if "Descripci" in str(c) or c == "Descripción"][:1]
    col_unnamed1 = [c for c in df.columns if "Unnamed: 1" in str(c)][:1]
    col_unnamed2 = [c for c in df.columns if "Unnamed: 2" in str(c)][:1]

    sensor_col = df.columns[0]
    mask_sensor = df[sensor_col].astype(str).str.contains("SN:", na=False)
    df["Sensor"] = df[sensor_col].where(mask_sensor).ffill()

    if col_unnamed1:
        mask_per = df[col_unnamed1[0]].astype(str).str.contains("per", case=False, na=False)
        df["Número de Periodo"] = df[col_unnamed1[0]].where(mask_per).ffill()
    else:
        df["Número de Periodo"] = None

    if col_unnamed2:
        df["Descripción"] = df[col_unnamed2[0]]
    elif col_desc:
        df["Descripción"] = df[col_desc[0]]

    if COL_READING not in df.columns:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    df[COL_READING] = pd.to_numeric(
        df[COL_READING].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
    df = df.dropna(subset=[COL_READING])
    if df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    df = df.rename(columns={k: v for k, v in COLUMN_RENAMES.items() if k in df.columns})
    out = df[[c for c in EXPECTED_COLUMNS if c in df.columns]].copy()
    for missing in EXPECTED_COLUMNS:
        if missing not in out.columns:
            out[missing] = None
    out = out[EXPECTED_COLUMNS]
    out["Tiempo de Inicio"] = pd.to_datetime(out["Tiempo de Inicio"], errors="coerce")
    out["Tiempo de finalización"] = pd.to_datetime(
        out["Tiempo de finalización"], errors="coerce"
    )
    return out


def load_processed_csv(path: Path | str) -> pd.DataFrame:
    """Carga un CSV ya normalizado (processed) al esquema canónico."""
    df = pd.read_csv(path)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV sin columnas esperadas: {missing}")
    out = df[EXPECTED_COLUMNS].copy()
    out[COL_READING] = pd.to_numeric(out[COL_READING], errors="coerce")
    out["Tiempo de Inicio"] = pd.to_datetime(out["Tiempo de Inicio"], errors="coerce")
    out["Tiempo de finalización"] = pd.to_datetime(
        out["Tiempo de finalización"], errors="coerce"
    )
    return out


def _reject_invalid_rows(
    df: pd.DataFrame, source_file: str
) -> tuple[pd.DataFrame, list[dict]]:
    rejected: list[dict[str, Any]] = []
    keep_mask = pd.Series(True, index=df.index)

    no_sensor = df["Sensor"].isna() | (df["Sensor"].astype(str).str.strip() == "")
    for idx in df.index[no_sensor]:
        rejected.append(
            {"source_file": source_file, "row": int(idx), "reason": "sensor_missing"}
        )
        keep_mask.loc[idx] = False

    no_reading = df[COL_READING].isna()
    for idx in df.index[no_reading & keep_mask]:
        rejected.append(
            {"source_file": source_file, "row": int(idx), "reason": "leyendo_invalid"}
        )
        keep_mask.loc[idx] = False

    no_start = df["Tiempo de Inicio"].isna()
    for idx in df.index[no_start & keep_mask]:
        rejected.append(
            {
                "source_file": source_file,
                "row": int(idx),
                "reason": "tiempo_inicio_invalid",
            }
        )
        keep_mask.loc[idx] = False

    return df.loc[keep_mask].copy(), rejected


def load_and_clean(paths: Sequence[Path | str] | Path | str) -> CleanResult:
    """Lee uno o más Excel dls_report, normaliza y valida filas."""
    if isinstance(paths, (str, Path)):
        path_list: list[Path] = [Path(paths)]
    else:
        path_list = [Path(p) for p in paths]

    frames: list[pd.DataFrame] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[str] = []
    transforms = [
        f"read_excel sheet={DLS_SHEET_NAME} header_row={DLS_HEADER_ROW}",
        "ffill Sensor and Número de Periodo",
        "coerce Leyendo to float (comma decimal)",
        "normalize datetime columns Tiempo de Inicio / Tiempo de finalización",
        f"enforce EXPECTED_COLUMNS ({len(EXPECTED_COLUMNS)} cols)",
    ]
    source_files: list[str] = []

    for path in path_list:
        source_files.append(path.name)
        if not path.exists():
            warnings.append(f"archivo_no_encontrado:{path.name}")
            continue
        try:
            raw = load_dls_report(path)
        except Exception as exc:  # noqa: BLE001 — documentar en log ETL
            warnings.append(f"error_lectura:{path.name}:{exc}")
            continue
        if raw.empty:
            warnings.append(f"sin_filas_validas:{path.name}")
            continue
        clean, file_rejected = _reject_invalid_rows(raw, path.name)
        rejected.extend(file_rejected)
        if not clean.empty:
            clean = clean.copy()
            clean["_source_file"] = path.name
            frames.append(clean)

    if not frames:
        return CleanResult(
            dataframe=pd.DataFrame(columns=[*EXPECTED_COLUMNS, "_source_file"]),
            rejected=rejected,
            warnings=warnings,
            source_files=source_files,
            transforms=transforms,
        )

    df = pd.concat(frames, ignore_index=True)
    return CleanResult(
        dataframe=df,
        rejected=rejected,
        warnings=warnings,
        source_files=source_files,
        transforms=transforms,
    )


def load_and_clean_csv(paths: Iterable[Path | str]) -> CleanResult:
    """Igual que load_and_clean pero para CSV processed."""
    frames: list[pd.DataFrame] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[str] = []
    source_files: list[str] = []
    transforms = [
        "read_csv processed schema",
        "coerce Leyendo and datetime columns",
        "validate Sensor / Leyendo / Tiempo de Inicio",
    ]

    for path in paths:
        p = Path(path)
        source_files.append(p.name)
        try:
            raw = load_processed_csv(p)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"error_lectura:{p.name}:{exc}")
            continue
        clean, file_rejected = _reject_invalid_rows(raw, p.name)
        rejected.extend(file_rejected)
        if not clean.empty:
            clean = clean.copy()
            clean["_source_file"] = p.name
            frames.append(clean)

    if not frames:
        return CleanResult(
            dataframe=pd.DataFrame(columns=[*EXPECTED_COLUMNS, "_source_file"]),
            rejected=rejected,
            warnings=warnings,
            source_files=source_files,
            transforms=transforms,
        )

    return CleanResult(
        dataframe=pd.concat(frames, ignore_index=True),
        rejected=rejected,
        warnings=warnings,
        source_files=source_files,
        transforms=transforms,
    )
