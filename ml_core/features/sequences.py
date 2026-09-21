"""Construcción de secuencias 3D [N, T, F] para modelos DL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from ml_core.features.build_features import (
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    TEST_MONTHS,
    engineer_features,
    load_readings_df,
    temporal_split,
)
from ml_core.features.targets import add_future_targets


@dataclass
class SequenceSplit:
    x_train: np.ndarray  # [N, T, F]
    y_class_train: np.ndarray
    y_reg_train: np.ndarray
    y_lead_train: np.ndarray
    x_test: np.ndarray
    y_class_test: np.ndarray
    y_reg_test: np.ndarray
    y_lead_test: np.ndarray
    feature_columns: list[str]
    lookback_steps: int
    horizon_minutes: float
    n_train: int
    n_test: int


def _windows_from_group(
    g: pd.DataFrame,
    *,
    lookback: int,
    feature_cols: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    g = g.dropna(subset=feature_cols + [LABEL_COLUMN, "y_reg", "y_alert_lead"]).copy()
    if len(g) < lookback:
        empty = np.zeros((0, lookback, len(feature_cols)))
        z = np.zeros(0)
        return empty, z, z, z, z

    feats = g[feature_cols].to_numpy(dtype=float)
    y_c = g[LABEL_COLUMN].to_numpy(dtype=int)
    y_r = g["y_reg"].to_numpy(dtype=float)
    y_l = g["y_alert_lead"].to_numpy(dtype=int)
    times = g["Tiempo de Inicio"].to_numpy()

    xs, yc, yr, yl, ts = [], [], [], [], []
    for i in range(lookback - 1, len(g)):
        if np.isnan(y_r[i]):
            continue
        window = feats[i - lookback + 1 : i + 1]
        if window.shape[0] != lookback:
            continue
        xs.append(np.nan_to_num(window, nan=0.0))
        yc.append(y_c[i])
        yr.append(y_r[i])
        yl.append(y_l[i])
        ts.append(times[i])

    if not xs:
        empty = np.zeros((0, lookback, len(feature_cols)))
        z = np.zeros(0)
        return empty, z, z, z, z

    return (
        np.stack(xs).astype(np.float32),
        np.asarray(yc, dtype=np.int64),
        np.asarray(yr, dtype=np.float32),
        np.asarray(yl, dtype=np.int64),
        np.asarray(ts),
    )


def dataframe_to_sequences(
    featured: pd.DataFrame,
    *,
    lookback_steps: int,
    test_months: int = TEST_MONTHS,
) -> SequenceSplit:
    split = temporal_split(featured, test_months=test_months)
    # Re-aplicar targets ya están en featured; filtrar por fechas del split
    train_df = featured[featured["Tiempo de Inicio"].isin(split.train["Tiempo de Inicio"])]
    # Mejor: usar mask por id si existe
    if "id" in featured.columns and "id" in split.train.columns:
        train_ids = set(split.train["id"].tolist())
        test_ids = set(split.test["id"].tolist())
        train_df = featured[featured["id"].isin(train_ids)]
        test_df = featured[featured["id"].isin(test_ids)]
    else:
        split_date = split.split_date
        train_df = featured[featured["Tiempo de Inicio"] < split_date]
        test_df = featured[featured["Tiempo de Inicio"] >= split_date]

    def pack(df: pd.DataFrame):
        xs, yc, yr, yl = [], [], [], []
        for _, g in df.groupby("sensor_id", sort=False):
            x, c, r, l, _ = _windows_from_group(
                g, lookback=lookback_steps, feature_cols=FEATURE_COLUMNS
            )
            if len(x):
                xs.append(x)
                yc.append(c)
                yr.append(r)
                yl.append(l)
        if not xs:
            f = len(FEATURE_COLUMNS)
            empty = np.zeros((0, lookback_steps, f), dtype=np.float32)
            z = np.zeros(0)
            return empty, z.astype(np.int64), z.astype(np.float32), z.astype(np.int64)
        return (
            np.concatenate(xs, axis=0),
            np.concatenate(yc, axis=0),
            np.concatenate(yr, axis=0),
            np.concatenate(yl, axis=0),
        )

    x_tr, yc_tr, yr_tr, yl_tr = pack(train_df)
    x_te, yc_te, yr_te, yl_te = pack(test_df)

    horizon = float(
        featured["_horizon_steps"].iloc[0] * featured["_delta_min"].iloc[0]
        if "_horizon_steps" in featured.columns and not featured.empty
        else settings.ml_lead_minutes_max
    )

    return SequenceSplit(
        x_train=x_tr,
        y_class_train=yc_tr,
        y_reg_train=yr_tr,
        y_lead_train=yl_tr,
        x_test=x_te,
        y_class_test=yc_te,
        y_reg_test=yr_te,
        y_lead_test=yl_te,
        feature_columns=list(FEATURE_COLUMNS),
        lookback_steps=lookback_steps,
        horizon_minutes=horizon,
        n_train=int(len(yc_tr)),
        n_test=int(len(yc_te)),
    )


def build_sequences(
    db: Session,
    *,
    max_rows: int | None = None,
    test_months: int = TEST_MONTHS,
    lookback_steps: int | None = None,
    horizon_minutes: float | None = None,
    lead_min: float | None = None,
    lead_max: float | None = None,
) -> SequenceSplit:
    lookback = lookback_steps or settings.ml_lookback_steps
    h = horizon_minutes if horizon_minutes is not None else (
        (settings.ml_lead_minutes_min + settings.ml_lead_minutes_max) / 2.0
    )
    lo = lead_min if lead_min is not None else float(settings.ml_lead_minutes_min)
    hi = lead_max if lead_max is not None else float(settings.ml_lead_minutes_max)

    raw = load_readings_df(db, max_rows=max_rows)
    featured = engineer_features(raw)
    featured = add_future_targets(
        featured, horizon_minutes=h, lead_min=lo, lead_max=hi
    )
    return dataframe_to_sequences(
        featured, lookback_steps=lookback, test_months=test_months
    )
