"""Eventos de inicio (onsets): no se premia un episodio ya en curso."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml_core.domain.thresholds import ThresholdSpec, is_violation


def onset_mask(values: np.ndarray, spec: ThresholdSpec) -> np.ndarray:
    """True en el primer paso de cada episodio de superación."""
    in_event = np.array([is_violation(float(v), spec) for v in values], dtype=bool)
    if in_event.size == 0:
        return in_event
    prev = np.concatenate([[False], in_event[:-1]])
    return in_event & ~prev


def count_onset_episodes(values: np.ndarray, spec: ThresholdSpec) -> int:
    return int(onset_mask(values, spec).sum())


def forecast_onset_labels(
    values: np.ndarray,
    spec: ThresholdSpec,
    *,
    k_max_steps: int,
) -> np.ndarray:
    """e_ℓ(t): cruzará el umbral en (t, t+k_max] y ahora no está en superación.

    Los instantes ya en superación quedan en 0 (no son inicios).
    """
    n = len(values)
    out = np.zeros(n, dtype=np.int8)
    if n == 0 or k_max_steps < 1:
        return out
    in_event = np.array([is_violation(float(v), spec) for v in values], dtype=bool)
    for t in range(n):
        if in_event[t]:
            continue
        end = min(n, t + 1 + k_max_steps)
        if in_event[t + 1 : end].any():
            out[t] = 1
    return out


def extract_event_spans(
    df: pd.DataFrame,
    spec: ThresholdSpec,
    *,
    value_col: str = "value",
    time_col: str = "ts",
    sensor_col: str = "sensor_code",
    gas_col: str = "gas",
) -> list[dict[str, object]]:
    """Episodios completos (inicio → fin) para un umbral. Reproducible."""
    if df.empty:
        return []
    sub = df[df[gas_col] == spec.gas_code].copy()
    if sub.empty:
        return []
    sub = sub.sort_values([sensor_col, time_col])
    events: list[dict[str, object]] = []
    for sensor, g in sub.groupby(sensor_col, sort=False):
        vals = g[value_col].to_numpy(dtype=float)
        times = pd.to_datetime(g[time_col], utc=True).to_numpy()
        in_event = [is_violation(float(v), spec) for v in vals]
        start_idx: int | None = None
        peak = None
        peak_at = None
        for i, flag in enumerate(in_event):
            if flag and start_idx is None:
                start_idx = i
                peak = float(vals[i])
                peak_at = times[i]
            elif flag and start_idx is not None:
                current = float(vals[i])
                if spec.direction == "below":
                    if peak is None or current < peak:
                        peak = current
                        peak_at = times[i]
                elif peak is None or current > peak:
                    peak = current
                    peak_at = times[i]
            elif not flag and start_idx is not None:
                events.append(
                    {
                        "sensor_code": str(sensor),
                        "gas_code": spec.gas_code,
                        "level": spec.level,
                        "started_at": pd.Timestamp(times[start_idx]).to_pydatetime(),
                        "ended_at": pd.Timestamp(times[i - 1]).to_pydatetime(),
                        "peak_value": peak,
                        "peak_at": pd.Timestamp(peak_at).to_pydatetime() if peak_at is not None else None,
                    }
                )
                start_idx = None
                peak = None
                peak_at = None
        if start_idx is not None:
            events.append(
                {
                    "sensor_code": str(sensor),
                    "gas_code": spec.gas_code,
                    "level": spec.level,
                    "started_at": pd.Timestamp(times[start_idx]).to_pydatetime(),
                    "ended_at": None,
                    "peak_value": peak,
                    "peak_at": pd.Timestamp(peak_at).to_pydatetime() if peak_at is not None else None,
                }
            )
    return events


def episodes_by_gas(
    df: pd.DataFrame,
    specs: list[ThresholdSpec],
    *,
    value_col: str = "value_canonical",
    gas_col: str = "gas",
    sensor_col: str = "sensor_code",
) -> list[dict[str, object]]:
    """Cuenta onsets por gas, sensor y nivel."""
    rows: list[dict[str, object]] = []
    if df.empty:
        return rows
    for spec in specs:
        sub = df[df[gas_col] == spec.gas_code]
        total = 0
        per_sensor: dict[str, int] = {}
        for sensor, g in sub.groupby(sensor_col, sort=False):
            vals = g[value_col].to_numpy(dtype=float)
            n = count_onset_episodes(vals, spec)
            per_sensor[str(sensor)] = n
            total += n
        rows.append(
            {
                "gas": spec.gas_code,
                "level": spec.level,
                "direction": spec.direction,
                "threshold": spec.value,
                "onsets": total,
                "sensors_with_onsets": sum(1 for n in per_sensor.values() if n > 0),
            }
        )
    return rows
