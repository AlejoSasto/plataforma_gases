"""Pruebas funcionales probables: varios gases suben y el oxígeno cae en 1–2 pasos."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd


def find_bump_intervals(
    frame: pd.DataFrame,
    *,
    instrument_col: str = "instrument",
    gas_col: str = "gas",
    time_col: str = "ts",
    value_col: str = "value",
    o2_drop: float = 0.4,
    min_other_gases: int = 2,
) -> list[dict[str, Any]]:
    """Intervalos [inicio, fin] por equipo. No modifica el marco."""
    if frame.empty:
        return []
    work = frame.copy()
    work[time_col] = pd.to_datetime(work[time_col], utc=True)
    intervals: list[dict[str, Any]] = []
    for instrument, group in work.groupby(instrument_col, sort=False):
        wide = (
            group.pivot_table(index=time_col, columns=gas_col, values=value_col, aggfunc="mean")
            .sort_index()
        )
        if "O2" not in wide.columns or len(wide) < 3:
            continue
        times = list(wide.index)
        for i in range(1, len(times)):
            o2 = wide["O2"]
            drop = float(o2.iloc[i - 1] - o2.iloc[i]) if pd.notna(o2.iloc[i]) and pd.notna(o2.iloc[i - 1]) else 0.0
            if drop < o2_drop:
                continue
            rising = 0
            for gas in wide.columns:
                if gas == "O2":
                    continue
                series = wide[gas]
                prev = series.iloc[i - 1]
                cur = series.iloc[i]
                if pd.isna(prev) or pd.isna(cur):
                    continue
                if float(cur) >= float(prev) * 1.5 or float(cur) - float(prev) >= 5:
                    rising += 1
            if rising < min_other_gases:
                continue
            start = times[i].to_pydatetime()
            end = times[min(i + 1, len(times) - 1)].to_pydatetime()
            intervals.append(
                {
                    "instrument": str(instrument),
                    "start": start,
                    "end": end + timedelta(seconds=1),
                }
            )
    return _merge_intervals(intervals)


def event_overlaps_bump(
    instrument: str,
    started_at: datetime,
    bumps: list[dict[str, Any]],
) -> bool:
    for bump in bumps:
        if bump["instrument"] != str(instrument):
            continue
        if bump["start"] <= started_at <= bump["end"]:
            return True
    return False


def _merge_intervals(intervals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda row: (row["instrument"], row["start"]))
    merged = [ordered[0]]
    for row in ordered[1:]:
        prev = merged[-1]
        if row["instrument"] == prev["instrument"] and row["start"] <= prev["end"]:
            prev["end"] = max(prev["end"], row["end"])
        else:
            merged.append(row)
    return merged
