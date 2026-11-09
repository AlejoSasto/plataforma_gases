"""Diagnóstico G1 sobre un marco de lecturas reales. No escribe en la base."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from ml_core.domain.bump import find_bump_intervals
from ml_core.domain.g1 import (
    choose_lookback_steps,
    eligible_models,
    event_eval_mode,
    merge_monthly_blocks,
    percentile,
)
from ml_core.domain.thresholds import THRESHOLD_SEED, is_violation


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "tiempo_inicio" in out.columns and "ts" not in out.columns:
        out["ts"] = out["tiempo_inicio"]
    if "leyendo" in out.columns and "value" not in out.columns:
        out["value"] = out["leyendo"]
    if "sensor_code" not in out.columns and "code" in out.columns:
        out["sensor_code"] = out["code"]
    if "gas" not in out.columns and "gas_type" in out.columns:
        out["gas"] = out["gas_type"]
    out["ts"] = pd.to_datetime(out["ts"], utc=True)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out["instrument"] = out["sensor_code"].astype(str)
    return out.dropna(subset=["ts", "value"])


def _segments(work: pd.DataFrame) -> dict[str, Any]:
    lengths: list[float] = []
    per_instrument: list[dict[str, Any]] = []
    for serial, group in work.groupby("instrument", sort=False):
        times = group["ts"].drop_duplicates().sort_values()
        if len(times) < 2:
            lengths.append(1)
            per_instrument.append({"serial": str(serial), "n_segments": 1, "steps": 1})
            continue
        diffs = times.diff().dt.total_seconds().dropna()
        median = float(diffs.median()) if len(diffs) else 360.0
        cut = 3 * median
        steps = 1
        segs: list[int] = []
        previous = times.iloc[0]
        for ts in times.iloc[1:]:
            gap = (ts - previous).total_seconds()
            if gap > cut:
                segs.append(steps)
                steps = 1
            else:
                steps += 1
            previous = ts
        segs.append(steps)
        lengths.extend(segs)
        gases = sorted(group["gas"].astype(str).unique())
        per_instrument.append(
            {
                "serial": str(serial),
                "gases": gases,
                "first": times.iloc[0].isoformat(),
                "last": times.iloc[-1].isoformat(),
                "n_segments": len(segs),
                "steps_p50": percentile([float(s) for s in segs], 50),
            }
        )
    return {
        "p10": percentile(lengths, 10),
        "p50": percentile(lengths, 50),
        "p90": percentile(lengths, 90),
        "instruments": per_instrument,
    }


def _episodes(work: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in THRESHOLD_SEED:
        sub = work[work["gas"] == spec.gas_code]
        n_ep = 0
        single = 0
        for _, group in sub.groupby("instrument", sort=False):
            ordered = group.sort_values("ts")
            values = ordered["value"].to_list()
            in_event = False
            length = 0
            for value in values:
                flag = is_violation(float(value), spec)
                if flag:
                    length += 1
                    in_event = True
                elif in_event:
                    n_ep += 1
                    if length == 1:
                        single += 1
                    in_event = False
                    length = 0
            if in_event:
                n_ep += 1
                if length == 1:
                    single += 1
        rows.append(
            {
                "gas": spec.gas_code,
                "level": spec.level,
                "metric": spec.metric,
                "n_episodes": n_ep,
                "single_step": single,
                "event_eval": event_eval_mode(n_ep),
            }
        )
    return rows


def _leyendo_semantics(work: pd.DataFrame) -> dict[str, Any]:
    conclusion = "instantáneo"
    detail = "No hay STEL ni TWA del instrumento para comparar."
    if "stel_max" in work.columns or "twa_max" in work.columns:
        ley = pd.to_numeric(work["value"], errors="coerce")
        stel = pd.to_numeric(work["stel_max"], errors="coerce") if "stel_max" in work.columns else None
        twa = pd.to_numeric(work["twa_max"], errors="coerce") if "twa_max" in work.columns else None
        d_stel = (ley - stel).abs().median() if stel is not None else None
        d_twa = (ley - twa).abs().median() if twa is not None else None
        if d_stel is not None and (d_twa is None or d_stel <= d_twa) and pd.notna(d_stel):
            conclusion = "máximo"
            detail = "Leyendo se parece más al STEL máximo del instrumento que al TWA."
        elif d_twa is not None and pd.notna(d_twa):
            conclusion = "promedio"
            detail = "Leyendo se parece más al TWA del instrumento que al STEL máximo."
        else:
            conclusion = "instantáneo"
            detail = "Leyendo no coincide con STEL ni con TWA; se trata como lectura del momento."
    return {"conclusion": conclusion, "detail": detail}


def _monthly_blocks(work: pd.DataFrame) -> list[dict[str, Any]]:
    work = work.copy()
    work["month"] = work["ts"].dt.strftime("%Y-%m")
    blocks = []
    for month, group in work.groupby("month", sort=True):
        blocks.append({"month": str(month), "n_valid": int(group["value"].notna().sum())})
    return blocks


def run_g1(df: pd.DataFrame, *, k_max: int = 3) -> dict[str, Any]:
    work = _prepare(df)
    segments = _segments(work)
    p50 = segments["p50"] if segments["p50"] is not None else 12
    lookback = choose_lookback_steps(int(round(p50)), k_max=k_max)
    kept, dropped = eligible_models(lookback)
    episodes = _episodes(work)
    blocks = merge_monthly_blocks(_monthly_blocks(work))
    bumps = find_bump_intervals(work)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(work)),
        "instruments": segments["instruments"],
        "segments": {"p10": segments["p10"], "p50": segments["p50"], "p90": segments["p90"]},
        "episodes": episodes,
        "leyendo": _leyendo_semantics(work),
        "bump_tests": [
            {"instrument": b["instrument"], "start": b["start"].isoformat(), "end": b["end"].isoformat()}
            for b in bumps
        ],
        "parameters": {
            "lookback_steps": lookback,
            "k_max": k_max,
            "eligible_models": kept,
            "excluded_models": dropped,
            "event_eval": {f"{e['gas']}:{e['level']}:{e['metric']}": e["event_eval"] for e in episodes},
            "folds": blocks,
        },
    }


def render_g1_markdown(report: dict[str, Any]) -> str:
    params = report["parameters"]
    lines = [
        "# Diagnóstico G1",
        "",
        f"Generado: `{report['generated_at']}`",
        "",
        "## Segmentos",
        "",
        f"- Duración en pasos: p10 {report['segments']['p10']}, p50 {report['segments']['p50']}, p90 {report['segments']['p90']}",
        f"- `lookback_steps`: **{params['lookback_steps']}**",
        "",
        "## Modelos que caben",
        "",
    ]
    for key in params["eligible_models"]:
        lines.append(f"- {key}")
    lines.append("")
    lines.append("## Modelos excluidos")
    lines.append("")
    for row in params["excluded_models"]:
        lines.append(f"- {row['model']}: {row['reason']}")
    lines += ["", "## Semántica de Leyendo", "", report["leyendo"]["detail"], ""]
    lines.append(f"Conclusión: **{report['leyendo']['conclusion']}**.")
    lines += ["", "## Pliegues", ""]
    for fold in params["folds"]:
        lines.append(f"- {fold['role']}: {', '.join(fold['months'])} ({fold['n_valid']} pasos)")
    lines.append("")
    return "\n".join(lines)
