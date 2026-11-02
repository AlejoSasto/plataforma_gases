"""Regla de selección lexicográfica. Sin preferencia por familia."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelectionResult:
    winner: str | None
    eligible: list[str]
    score: dict[str, Any]
    reason: str
    ranking: list[str] = field(default_factory=list)


def _num(row: dict[str, Any], key: str, default: float = float("inf")) -> float:
    v = row.get(key)
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x if x == x else default  # NaN


def is_eligible(
    row: dict[str, Any],
    *,
    coverage_target: float = 0.90,
    coverage_tol: float = 0.05,
) -> bool:
    mase = _num(row, "mase", 99.0)
    cov = _num(row, "coverage_10_90", 0.0)
    return mase < 1.0 and abs(cov - coverage_target) <= coverage_tol


def select_production_model(
    evaluations: list[dict[str, Any]],
    *,
    fa_limit: float = 1.0,
    coverage_target: float = 0.90,
    coverage_tol: float = 0.05,
) -> SelectionResult:
    """Orden: elegibilidad → recall actuar → anticipación p50 → menos FA → menor latencia."""
    if not evaluations:
        return SelectionResult(None, [], {}, "sin evaluaciones", [])

    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in evaluations:
        if row.get("is_final_test"):
            continue
        name = str(row.get("model") or row.get("name") or row.get("algorithm") or "")
        by_name.setdefault(name, []).append(row)

    aggregated: list[dict[str, Any]] = []
    for name, rows in by_name.items():
        def mean(key: str, default: float = float("nan")) -> float:
            vals = [_num(r, key, default) for r in rows]
            vals = [v for v in vals if v == v and v != float("inf")]
            return float(sum(vals) / len(vals)) if vals else default

        aggregated.append(
            {
                "model": name,
                "family": rows[0].get("family"),
                "mase": mean("mase"),
                "coverage_10_90": mean("coverage_10_90"),
                "recall": mean("recall"),
                "lead_p50": mean("lead_p50", 0.0),
                "fa_per_shift": mean("fa_per_shift", 99.0),
                "latency_ms": mean("latency_ms", 99_000.0),
            }
        )

    eligible = [r for r in aggregated if is_eligible(r, coverage_target=coverage_target, coverage_tol=coverage_tol)]
    pool = eligible or aggregated
    fa_ok = [r for r in pool if _num(r, "fa_per_shift", 99) <= fa_limit]
    if fa_ok:
        pool = fa_ok

    def sort_key(r: dict[str, Any]) -> tuple:
        return (
            -_num(r, "recall", 0.0),
            -_num(r, "lead_p50", 0.0),
            _num(r, "fa_per_shift", 99.0),
            _num(r, "latency_ms", 99_000.0),
            str(r["model"]),
        )

    ranked = sorted(pool, key=sort_key)
    winner = ranked[0]["model"] if ranked else None
    reason = "elegible por MASE<1 y cobertura" if eligible else "nadie elegible; se propone el de mayor recall (no promover a ciegas)"
    return SelectionResult(
        winner=winner,
        eligible=[r["model"] for r in eligible],
        score=ranked[0] if ranked else {},
        reason=reason,
        ranking=[r["model"] for r in ranked],
    )
