"""Feature engineering sobre gas_readings (Plan 04)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

FEATURE_COLUMNS = ["Leyendo", "Media_Movil", "Cambio", "Cambio_Brusco", "Temperatura"]
LABEL_COLUMN = "evento_final"
ROLLING_WINDOW = 20
TEST_MONTHS = 3


@dataclass
class FeatureSplit:
    train: pd.DataFrame
    test: pd.DataFrame
    feature_columns: list[str]
    label_column: str
    n_positive: int
    n_total: int
    date_min: Optional[pd.Timestamp]
    date_max: Optional[pd.Timestamp]
    split_date: Optional[pd.Timestamp]


def load_readings_df(db: Session, max_rows: int | None = None) -> pd.DataFrame:
    """Carga lecturas desde PostgreSQL ordenadas por sensor y tiempo."""
    limit_sql = f"LIMIT {int(max_rows)}" if max_rows else ""
    sql = text(
        f"""
        SELECT
            gr.id,
            gr.sensor_id,
            s.code AS sensor_code,
            s.gas_type,
            si.name AS site_name,
            gr.leyendo AS "Leyendo",
            gr.stel_max,
            gr.twa_max,
            gr.alarma,
            gr.temperatura AS "Temperatura",
            gr.tiempo_inicio AS "Tiempo de Inicio",
            gr.is_synthetic
        FROM gas_readings gr
        JOIN sensors s ON s.id = gr.sensor_id
        JOIN sites si ON si.id = s.site_id
        ORDER BY gr.sensor_id, gr.tiempo_inicio
        {limit_sql}
        """
    )
    df = pd.read_sql(sql, db.get_bind())
    if not df.empty:
        df["Tiempo de Inicio"] = pd.to_datetime(df["Tiempo de Inicio"], utc=True)
    return df


def _add_sensor_features(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("Tiempo de Inicio").copy()
    g["Media_Movil"] = g["Leyendo"].rolling(window=ROLLING_WINDOW, min_periods=1).mean()
    g["Cambio"] = g["Leyendo"].diff().abs().fillna(0.0)
    mean_c = g["Cambio"].mean()
    std_c = g["Cambio"].std(ddof=0)
    threshold = mean_c + 2 * (std_c if pd.notna(std_c) else 0.0)
    g["Cambio_Brusco"] = (g["Cambio"] > threshold).astype(int)
    return g


def _add_evento_final(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Leyendo"] = pd.to_numeric(out["Leyendo"], errors="coerce")
    # Percentil 95 por sensor
    out["_p95"] = out.groupby("sensor_id")["Leyendo"].transform(
        lambda s: s.quantile(0.95)
    )
    alarma = out["alarma"].fillna("").astype(str).str.strip()
    has_alarma = alarma.ne("") & alarma.str.lower().ne("nan") & alarma.str.lower().ne("none")
    stel = pd.to_numeric(out["stel_max"], errors="coerce")
    over_stel = stel.notna() & (out["Leyendo"] > stel)
    over_p95 = out["_p95"].notna() & (out["Leyendo"] > out["_p95"])
    out[LABEL_COLUMN] = (has_alarma | over_stel | over_p95).fillna(False).astype(int)
    out = out.drop(columns=["_p95"])
    return out


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    parts = [_add_sensor_features(g) for _, g in df.groupby("sensor_id", sort=False)]
    featured = pd.concat(parts, ignore_index=True)
    featured = _add_evento_final(featured)
    featured["Temperatura"] = pd.to_numeric(featured["Temperatura"], errors="coerce")
    featured["Leyendo"] = pd.to_numeric(featured["Leyendo"], errors="coerce")
    return featured


def temporal_split(df: pd.DataFrame, test_months: int = TEST_MONTHS) -> FeatureSplit:
    work = df.dropna(subset=FEATURE_COLUMNS + [LABEL_COLUMN]).copy()
    if work.empty:
        return FeatureSplit(
            train=work,
            test=work,
            feature_columns=FEATURE_COLUMNS,
            label_column=LABEL_COLUMN,
            n_positive=0,
            n_total=0,
            date_min=None,
            date_max=None,
            split_date=None,
        )

    date_max = work["Tiempo de Inicio"].max()
    date_min = work["Tiempo de Inicio"].min()
    split_date = date_max - pd.DateOffset(months=test_months)
    train = work[work["Tiempo de Inicio"] < split_date].copy()
    test = work[work["Tiempo de Inicio"] >= split_date].copy()

    # Si el split deja un lado vacío (pocos datos), usar 80/20 temporal
    if train.empty or test.empty:
        cutoff = work["Tiempo de Inicio"].quantile(0.8)
        train = work[work["Tiempo de Inicio"] < cutoff].copy()
        test = work[work["Tiempo de Inicio"] >= cutoff].copy()
        split_date = cutoff

    return FeatureSplit(
        train=train,
        test=test,
        feature_columns=FEATURE_COLUMNS,
        label_column=LABEL_COLUMN,
        n_positive=int(work[LABEL_COLUMN].sum()),
        n_total=int(len(work)),
        date_min=date_min,
        date_max=date_max,
        split_date=split_date,
    )


def build_features(
    db: Session,
    *,
    max_rows: int | None = None,
    test_months: int = TEST_MONTHS,
) -> FeatureSplit:
    raw = load_readings_df(db, max_rows=max_rows)
    featured = engineer_features(raw)
    return temporal_split(featured, test_months=test_months)
