"""Diagnóstico de datos reales (Plan 15 F0). Solo lectura. Idempotente."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from ml_core.domain.events import episodes_by_gas
from ml_core.domain.thresholds import PRIORITY_GASES, THRESHOLD_SEED
from ml_core.domain.units import CanonicalUnitError, to_canonical


def _canonicalize_gas(raw: Optional[str]) -> str:
    from app.shared.gas_catalog import canonicalize_gas_type

    return canonicalize_gas_type(raw)


def _canonicalize_sensor(raw: Optional[str]) -> str:
    from app.shared.gas_catalog import normalize_sensor_code

    return normalize_sensor_code(raw)


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza un consolidado CSV o un extracto de gas_readings a columnas internas."""
    out = df.copy()
    rename = {
        "Leyendo": "leyendo",
        "Gas": "gas_raw",
        "Sensor": "sensor_raw",
        "Unidad": "unidad",
        "Tiempo de Inicio": "tiempo_inicio",
        "Tiempo de finalización": "tiempo_fin",
        "gas_type": "gas_raw",
        "code": "sensor_raw",
    }
    for src, dst in rename.items():
        if src in out.columns and dst not in out.columns:
            out[dst] = out[src]
    if "gas" not in out.columns:
        raw_gas = out["gas_raw"] if "gas_raw" in out.columns else out.get("Descripción")
        out["gas"] = [ _canonicalize_gas(v) for v in raw_gas.tolist() ] if raw_gas is not None else "UNKNOWN"
    else:
        out["gas"] = [ _canonicalize_gas(v) for v in out["gas"].tolist() ]
    if "sensor_code" not in out.columns:
        raw_s = out["sensor_raw"] if "sensor_raw" in out.columns else out.get("Sensor")
        out["sensor_code"] = (
            [_canonicalize_sensor(v) for v in raw_s.tolist()] if raw_s is not None else "SENSOR-DESCONOCIDO"
        )
    out["tiempo_inicio"] = pd.to_datetime(out["tiempo_inicio"], utc=True, errors="coerce")
    if "tiempo_fin" in out.columns:
        out["tiempo_fin"] = pd.to_datetime(out["tiempo_fin"], utc=True, errors="coerce")
    out["leyendo"] = pd.to_numeric(out["leyendo"], errors="coerce")
    out = out.dropna(subset=["leyendo", "tiempo_inicio", "sensor_code", "gas"])
    if "is_synthetic" in out.columns:
        out = out.loc[~out["is_synthetic"].astype(bool)].copy()

    values: list[float] = []
    units: list[str] = []
    unknown: list[bool] = []
    for _, row in out.iterrows():
        try:
            v, u = to_canonical(
                float(row["leyendo"]),
                gas_code=str(row["gas"]),
                unit=row.get("unidad"),
            )
            values.append(v)
            units.append(u)
            unknown.append(False)
        except (CanonicalUnitError, TypeError, ValueError):
            values.append(float(row["leyendo"]))
            units.append(str(row.get("unidad") or ""))
            unknown.append(True)
    out["value_canonical"] = values
    out["unit_canonical"] = units
    out["unidad_desconocida"] = unknown
    return out.sort_values(["sensor_code", "gas", "tiempo_inicio"]).reset_index(drop=True)


def _interval_stats(times: pd.Series) -> dict[str, Any]:
    times = times.dropna().sort_values()
    if len(times) < 2:
        return {
            "n": int(len(times)),
            "dt_p10_min": None,
            "dt_p50_min": None,
            "dt_p90_min": None,
            "gap_gt_3median_pct": None,
        }
    deltas = times.diff().dt.total_seconds().dropna() / 60.0
    deltas = deltas[deltas > 0]
    if deltas.empty:
        return {
            "n": int(len(times)),
            "dt_p10_min": None,
            "dt_p50_min": None,
            "dt_p90_min": None,
            "gap_gt_3median_pct": None,
        }
    p10, p50, p90 = (float(deltas.quantile(q)) for q in (0.1, 0.5, 0.9))
    gap_pct = float((deltas > 3 * p50).mean() * 100.0) if p50 and p50 > 0 else 0.0
    return {
        "n": int(len(times)),
        "dt_p10_min": round(p10, 4),
        "dt_p50_min": round(p50, 4),
        "dt_p90_min": round(p90, 4),
        "gap_gt_3median_pct": round(gap_pct, 2),
    }


def _infer_sensor_kind(times: pd.Series) -> str:
    """portatil si sesiones cortas separadas por huecos largos; fijo si cobertura continua."""
    times = times.dropna().sort_values()
    n = len(times)
    if n < 4:
        return "desconocido"
    deltas_h = times.diff().dt.total_seconds().dropna() / 3600.0
    session_gap_h = 6.0
    n_sessions = int((deltas_h > session_gap_h).sum()) + 1
    span_days = (times.iloc[-1] - times.iloc[0]).total_seconds() / 86400.0
    if span_days <= 0:
        return "desconocido"
    days_with_data = times.dt.floor("D").nunique()
    coverage = days_with_data / max(span_days, 1)
    # Duración mediana de sesión
    session_breaks = np.concatenate([[0], (deltas_h > session_gap_h).astype(int).cumsum().to_numpy()])
    sid = pd.Series(session_breaks, index=times.index)
    durations = []
    for _, g in times.groupby(sid):
        if len(g) >= 2:
            durations.append((g.iloc[-1] - g.iloc[0]).total_seconds() / 3600.0)
    med_session_h = float(np.median(durations)) if durations else span_days * 24
    if n_sessions >= 2 and med_session_h <= 24 and coverage < 0.45:
        return "portatil"
    if span_days >= 7 and coverage >= 0.4:
        return "fijo"
    if med_session_h <= 24:
        return "portatil"
    return "desconocido"


def per_sensor(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    grouped = df.groupby(["sensor_code", "gas"], sort=False)
    for (sensor, gas), g in grouped:
        times = g["tiempo_inicio"]
        stats = _interval_stats(times)
        stats.update(
            {
                "sensor_code": str(sensor),
                "gas": str(gas),
                "t_min": times.min().isoformat() if len(times) else None,
                "t_max": times.max().isoformat() if len(times) else None,
                "kind": _infer_sensor_kind(times),
                "units": sorted({str(u) for u in g["unidad"].dropna().astype(str).unique()})
                if "unidad" in g.columns
                else [],
            }
        )
        rows.append(stats)
    return rows


def density_by_month_gas(df: pd.DataFrame) -> list[dict[str, Any]]:
    tmp = df.copy()
    tmp["month"] = tmp["tiempo_inicio"].dt.strftime("%Y-%m")
    counts = tmp.groupby(["month", "gas"]).size().reset_index(name="n")
    return counts.to_dict(orient="records")


def units_by_gas(df: pd.DataFrame) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if "unidad" not in df.columns:
        return out
    for gas, g in df.groupby("gas"):
        out[str(gas)] = sorted({str(u) for u in g["unidad"].dropna().astype(str).unique()})
    return out


def duplicates_report(df: pd.DataFrame) -> dict[str, Any]:
    key_exact = ["sensor_code", "gas", "tiempo_inicio", "leyendo"]
    exact = int(df.duplicated(subset=key_exact, keep="first").sum())
    near = 0
    for _, g in df.groupby(["sensor_code", "gas"]):
        g = g.sort_values("tiempo_inicio")
        if len(g) < 2:
            continue
        dt = g["tiempo_inicio"].diff().dt.total_seconds().fillna(9999)
        dv = g["leyendo"].diff().abs().fillna(9999)
        near += int(((dt > 0) & (dt <= 60) & (dv <= 1e-9)).sum())
    return {"exact": exact, "near_same_value_within_60s": near}


def g0_decision(sensor_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Horizonte posible a partir de la mediana Δt de gases prioritarios."""
    per_gas: dict[str, list[float]] = {g: [] for g in PRIORITY_GASES}
    for row in sensor_rows:
        gas = row.get("gas")
        p50 = row.get("dt_p50_min")
        if gas in per_gas and p50 is not None:
            per_gas[str(gas)].append(float(p50))
    gas_medians: dict[str, Optional[float]] = {}
    for gas, vals in per_gas.items():
        gas_medians[gas] = round(float(np.median(vals)), 4) if vals else None
    present = [v for v in gas_medians.values() if v is not None]
    dt = max(present) if present else None
    if dt is None:
        band = "sin_datos"
        horizons: list[int] = []
        note = "No hay intervalos calculables en gases prioritarios."
    elif dt <= 2:
        band = "fine"
        horizons = [5, 10]
        note = "Δt ≤ 2 min: se pueden prometer horizontes de 5 y 10 min."
    elif dt <= 10:
        step = max(1, int(round(dt)))
        band = "medium"
        horizons = [step, 2 * step, 3 * step]
        note = (
            f"2 < Δt ≤ 10 min (Δt={dt:.2f}). Horizontes = 1, 2 y 3 pasos. "
            "Solicitar al proveedor el export de datalog por intervalo."
        )
    else:
        step = max(1, int(round(dt)))
        band = "coarse"
        horizons = [step, 2 * step, 3 * step]
        note = (
            f"Δt > 10 min (Δt={dt:.2f}): no se sostiene alerta a 5–10 min. "
            "Solicitar datalog crudo iNet. Evaluar en el horizonte que el dato permite "
            "y declararlo como limitación de la tesis."
        )
    return {
        "dt_p50_min_priority_max": dt,
        "dt_p50_min_by_gas": gas_medians,
        "band": band,
        "horizons_min": horizons,
        "note": note,
    }


def event_policy(onsets: int) -> str:
    if onsets >= 30:
        return "bootstrap_ic"
    if onsets >= 10:
        return "wide_ic_warning"
    return "no_event_metrics"


def run_diagnosis(df: pd.DataFrame, *, source: str) -> dict[str, Any]:
    prepared = prepare_frame(df)
    sensors = per_sensor(prepared)
    episodes = episodes_by_gas(prepared, list(THRESHOLD_SEED))
    for ep in episodes:
        ep["policy"] = event_policy(int(ep["onsets"]))
    g0 = g0_decision(sensors)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "n_rows": int(len(prepared)),
        "n_sensors": int(prepared.groupby(["sensor_code", "gas"]).ngroups) if len(prepared) else 0,
        "gases": sorted(prepared["gas"].unique().tolist()) if len(prepared) else [],
        "t_min": prepared["tiempo_inicio"].min().isoformat() if len(prepared) else None,
        "t_max": prepared["tiempo_inicio"].max().isoformat() if len(prepared) else None,
        "sensors": sensors,
        "density_month_gas": density_by_month_gas(prepared),
        "units_by_gas": units_by_gas(prepared),
        "duplicates": duplicates_report(prepared),
        "episodes": episodes,
        "g0": g0,
        "thresholds_verified": False,
        "lel_ch4_percent_vol": 5.0,
    }
    return result
