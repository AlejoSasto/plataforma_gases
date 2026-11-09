"""Parámetros automáticos de la compuerta G1 (Plan 25 F1).

Las reglas son puras: el mismo insumo produce el mismo resultado.
"""

from __future__ import annotations

from typing import Any

# Contexto mínimo documentado al instalar cada adaptador (pasos de la rejilla).
MIN_CONTEXT_STEPS: dict[str, int] = {
    "persistencia": 1,
    "ets": 8,
    "lgbm_q": 30,
    "lstm": 30,
    "tft": 48,
    "chronos": 64,
    "chronos2": 64,
    "timesfm": 32,
    "patchtst": 48,
    "itransformer": 48,
    "ttm": 32,
}

CANDIDATE_LOOKBACKS: tuple[int, ...] = (30, 60, 120)
FINAL_ZOO: tuple[str, ...] = (
    "persistencia",
    "ets",
    "lgbm_q",
    "lstm",
    "tft",
    "chronos",
    "chronos2",
    "timesfm",
)
OPTIONAL_ZOO: tuple[str, ...] = ("patchtst", "itransformer", "ttm")


def choose_lookback_steps(segment_p50_steps: int, *, k_max: int = 3) -> int:
    """Mayor de {30, 60, 120} que quepa en p50 − k_max. Si ninguno, max(12, p50 − k_max)."""
    room = int(segment_p50_steps) - int(k_max)
    fitting = [w for w in CANDIDATE_LOOKBACKS if w <= room]
    if fitting:
        return max(fitting)
    return max(12, room)


def event_eval_mode(n_episodes: int) -> str:
    return "por_episodio" if int(n_episodes) >= 10 else "solo_pronostico"


def eligible_models(lookback_steps: int) -> tuple[list[str], list[dict[str, str]]]:
    """Excluye quien pida más contexto que w. La ablación opcional solo entra si cabe."""
    kept: list[str] = []
    dropped: list[dict[str, str]] = []
    w = int(lookback_steps)
    for key, need in MIN_CONTEXT_STEPS.items():
        if key in OPTIONAL_ZOO and need > w:
            dropped.append(
                {
                    "model": key,
                    "reason": f"contexto mínimo documentado {need} supera w={w}; queda fuera de la ablación",
                }
            )
            continue
        if need <= w:
            kept.append(key)
        else:
            dropped.append(
                {
                    "model": key,
                    "reason": f"contexto mínimo documentado {need} supera w={w}",
                }
            )
    return kept, dropped


def merge_monthly_blocks(
    blocks: list[dict[str, Any]],
    *,
    min_valid: int = 500,
) -> list[dict[str, Any]]:
    """Fusiona meses contiguos hasta ≥ min_valid pasos. El último bloque es final_test."""
    if not blocks:
        return []
    body = list(blocks[:-1])
    last = blocks[-1]
    merged: list[dict[str, Any]] = []
    buf: list[dict[str, Any]] = []
    acc = 0
    for block in body:
        buf.append(block)
        acc += int(block.get("n_valid") or 0)
        if acc >= min_valid:
            merged.append(
                {
                    "months": [str(b.get("month")) for b in buf],
                    "n_valid": acc,
                    "role": "validacion",
                }
            )
            buf = []
            acc = 0
    if buf:
        extra_months = [str(b.get("month")) for b in buf]
        extra_n = acc
        if merged:
            merged[-1]["months"].extend(extra_months)
            merged[-1]["n_valid"] = int(merged[-1]["n_valid"]) + extra_n
        else:
            merged.append({"months": extra_months, "n_valid": extra_n, "role": "validacion"})
    merged.append(
        {
            "months": [str(last.get("month"))],
            "n_valid": int(last.get("n_valid") or 0),
            "role": "final_test",
        }
    )
    return merged


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * (q / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac
