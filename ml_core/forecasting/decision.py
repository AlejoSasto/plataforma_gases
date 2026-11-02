"""Capa de decisión normativa: cuantiles → nivel → aviso (Plan 17 §5)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ml_core.domain.thresholds import ThresholdSpec, is_violation

LEVEL_RANK = {"normal": 0, "vigilar": 1, "actuar": 2, "evacuar": 3}
LEVELS = ("vigilar", "actuar", "evacuar")


def _interp_cdf(quantiles: dict[float, float], value: float) -> float:
    """CDF empírica lineal entre (0.10, 0.50, 0.90, 0.95)."""
    pts = sorted((float(t), float(q)) for t, q in quantiles.items() if np.isfinite(q))
    if not pts:
        return 0.5
    xs = [p[1] for p in pts]
    ts = [p[0] for p in pts]
    v = float(value)
    if v <= xs[0]:
        return max(0.0, ts[0] * v / xs[0]) if xs[0] != 0 else 0.0
    if v >= xs[-1]:
        extra = min(1.0, ts[-1] + (1 - ts[-1]) * 0.5)
        return extra if v > xs[-1] else ts[-1]
    for i in range(1, len(xs)):
        if v <= xs[i]:
            w = (v - xs[i - 1]) / max(xs[i] - xs[i - 1], 1e-12)
            return float(ts[i - 1] + w * (ts[i] - ts[i - 1]))
    return 1.0


def exceedance_probability(
    *,
    q10: float,
    q50: float,
    q90: float,
    q95: float,
    threshold: float,
    direction: str,
) -> float:
    """P(C ≥ θ) o P(C ≤ θ) interpolando la distribución predictiva."""
    cdf = _interp_cdf({0.10: q10, 0.50: q50, 0.90: q90, 0.95: q95}, threshold)
    cdf = float(np.clip(cdf, 0.0, 1.0))
    if direction == "below":
        return cdf
    return 1.0 - cdf


def fit_decision_threshold(
    scores: np.ndarray,
    event: np.ndarray,
    *,
    fa_per_shift_max: float,
    shift_hours: float,
    step_minutes: float,
    min_recall: float = 0.95,
) -> dict[str, float]:
    """Elige π que maximiza recall sujeto a falsas alarmas/turno ≤ límite."""
    s = np.asarray(scores, dtype=float)
    e = np.asarray(event, dtype=int)
    n = s.size
    if n == 0:
        return {"pi": 0.5, "recall": 0.0, "fa_per_shift": 0.0, "constrained": False}
    steps_per_shift = max(1.0, (shift_hours * 60.0) / max(step_minutes, 1.0))
    n_shifts = max(n / steps_per_shift, 1e-6)
    n_pos = int(e.sum())
    best = {"pi": 0.5, "recall": 0.0, "fa_per_shift": 0.0, "constrained": False}
    for pi in np.linspace(0.05, 0.95, 37):
        pred = (s >= pi).astype(int)
        tp = int(((pred == 1) & (e == 1)).sum())
        fp = int(((pred == 1) & (e == 0)).sum())
        recall = (tp / n_pos) if n_pos else 0.0
        fa = fp / n_shifts
        ok = fa <= fa_per_shift_max
        better = recall > best["recall"] + 1e-9 or (
            abs(recall - best["recall"]) < 1e-9 and fa < best["fa_per_shift"]
        )
        if ok and better:
            best = {"pi": float(pi), "recall": float(recall), "fa_per_shift": float(fa), "constrained": True}
    if best["constrained"]:
        return best
    # Priorizar recall y registrar la tasa resultante
    for pi in np.linspace(0.05, 0.95, 37):
        pred = (s >= pi).astype(int)
        tp = int(((pred == 1) & (e == 1)).sum())
        fp = int(((pred == 1) & (e == 0)).sum())
        recall = (tp / n_pos) if n_pos else 0.0
        fa = fp / n_shifts
        if recall > best["recall"] + 1e-9 or (
            abs(recall - best["recall"]) < 1e-9 and fa < best["fa_per_shift"]
        ):
            best = {"pi": float(pi), "recall": float(recall), "fa_per_shift": float(fa), "constrained": False}
    return best


@dataclass
class DecisionState:
    """Persistencia e histéresis para no parpadear avisos."""

    persistence_steps: int = 2
    hysteresis: float = 0.8
    pi: dict[str, float] = field(default_factory=lambda: {"vigilar": 0.4, "actuar": 0.55, "evacuar": 0.75})
    _streak: dict[str, int] = field(default_factory=lambda: {k: 0 for k in LEVELS})
    current: str = "normal"

    def update(self, probs: dict[str, float]) -> str:
        proposed = "normal"
        for level in reversed(LEVELS):
            p = float(probs.get(level, 0.0))
            pi = float(self.pi.get(level, 0.5))
            if p >= pi:
                self._streak[level] = self._streak.get(level, 0) + 1
            elif self.current == level and p >= self.hysteresis * pi:
                self._streak[level] = max(self._streak.get(level, 0), self.persistence_steps)
            else:
                self._streak[level] = 0
            if self._streak[level] >= self.persistence_steps:
                proposed = level
                break
        if LEVEL_RANK[proposed] < LEVEL_RANK[self.current]:
            cur_pi = float(self.pi.get(self.current, 0.5)) if self.current in self.pi else 0.5
            p_cur = float(probs.get(self.current, 0.0))
            if p_cur >= self.hysteresis * cur_pi:
                proposed = self.current
        self.current = proposed
        return self.current


def confirmed_level(value: float, specs: list[ThresholdSpec]) -> str | None:
    """Aviso confirmado: la lectura actual ya superó el umbral. No usa el modelo."""
    hit = None
    rank = -1
    for spec in specs:
        if is_violation(float(value), spec) and LEVEL_RANK.get(spec.level, -1) > rank:
            hit = spec.level
            rank = LEVEL_RANK[spec.level]
    return hit


def operational_level(confirmed: str | None, anticipated: str) -> str:
    c = confirmed or "normal"
    a = anticipated or "normal"
    return c if LEVEL_RANK.get(c, 0) >= LEVEL_RANK.get(a, 0) else a


def probs_for_horizon(
    q10: float,
    q50: float,
    q90: float,
    q95: float,
    specs: list[ThresholdSpec],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for spec in specs:
        out[spec.level] = exceedance_probability(
            q10=q10,
            q50=q50,
            q90=q90,
            q95=q95,
            threshold=float(spec.value),
            direction=spec.direction,
        )
    return out
