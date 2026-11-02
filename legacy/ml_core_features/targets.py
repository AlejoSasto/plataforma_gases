"""Targets temporales: regresión a horizonte y alerta anticipada."""

from __future__ import annotations

import numpy as np
import pandas as pd

from legacy.ml_core_features.build_features import LABEL_COLUMN


def median_delta_minutes(times: pd.Series) -> float:
    """Mediana del intervalo entre lecturas en minutos (mínimo 0.1)."""
    t = pd.to_datetime(times, utc=True).sort_values()
    if len(t) < 2:
        return 1.0
    diffs = t.diff().dt.total_seconds().dropna() / 60.0
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return 1.0
    return float(max(0.1, diffs.median()))


def horizon_steps_from_minutes(delta_minutes: float, horizon_minutes: float) -> int:
    steps = int(round(horizon_minutes / max(delta_minutes, 0.1)))
    return max(1, steps)


def add_future_targets(
    df: pd.DataFrame,
    *,
    horizon_minutes: float = 7.5,
    lead_min: float = 5.0,
    lead_max: float = 10.0,
) -> pd.DataFrame:
    """
    Por sensor añade:
    - y_reg: Leyendo en t+h
    - y_alert_lead: 1 si hay evento_final en ventana [t+lead_min, t+lead_max]
    """
    parts: list[pd.DataFrame] = []
    for _, g in df.groupby("sensor_id", sort=False):
        g = g.sort_values("Tiempo de Inicio").copy()
        delta = median_delta_minutes(g["Tiempo de Inicio"])
        h_steps = horizon_steps_from_minutes(delta, horizon_minutes)
        lead_lo = horizon_steps_from_minutes(delta, lead_min)
        lead_hi = horizon_steps_from_minutes(delta, lead_max)

        g["y_reg"] = g["Leyendo"].shift(-h_steps)
        g["_delta_min"] = delta
        g["_horizon_steps"] = h_steps

        # Evento futuro en ventana lead
        events = g[LABEL_COLUMN].to_numpy(dtype=int)
        n = len(g)
        lead = np.zeros(n, dtype=int)
        for i in range(n):
            a = i + lead_lo
            b = min(n, i + lead_hi + 1)
            if a < n and events[a:b].any():
                lead[i] = 1
        g["y_alert_lead"] = lead
        parts.append(g)

    if not parts:
        return df
    return pd.concat(parts, ignore_index=True)
