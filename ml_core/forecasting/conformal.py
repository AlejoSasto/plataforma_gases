"""Calibración conformal de cuantiles e intervalo (Plan 17 §4).

Implementación propia: no depende de APIs de terceros.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def _finite(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(a) & np.isfinite(b)
    return a[mask], b[mask]


def split_conformal_offset(y: np.ndarray, q_hat: np.ndarray, *, tau: float) -> float:
    """Desplazamiento aditivo para que el cuantil empírico alcance τ."""
    yt, qh = _finite(np.asarray(y, dtype=float), np.asarray(q_hat, dtype=float))
    if yt.size < 8:
        return 0.0
    resid = yt - qh
    target = float(np.clip(tau, 0.01, 0.99))
    # (n+1)/n para cobertura finita
    q_level = min(1.0, np.ceil((yt.size + 1) * target) / yt.size)
    return float(np.quantile(resid, q_level))


def interval_conformal_offset(
    y: np.ndarray,
    q_lo: np.ndarray,
    q_hi: np.ndarray,
    *,
    target: float = 0.90,
) -> float:
    """Score de intervalo: max(q_lo - y, y - q_hi). Cubre `target` de los casos."""
    yt, lo = _finite(np.asarray(y, dtype=float), np.asarray(q_lo, dtype=float))
    _, hi = _finite(np.asarray(y, dtype=float), np.asarray(q_hi, dtype=float))
    n = min(yt.size, lo.size, hi.size)
    if n < 8:
        return 0.0
    yt, lo, hi = yt[:n], lo[:n], hi[:n]
    scores = np.maximum(lo - yt, yt - hi)
    return float(np.quantile(scores, float(target)))


def coverage(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    yt, l = _finite(np.asarray(y, dtype=float), np.asarray(lo, dtype=float))
    _, h = _finite(np.asarray(y, dtype=float), np.asarray(hi, dtype=float))
    n = min(yt.size, l.size, h.size)
    if n == 0:
        return float("nan")
    inside = (yt[:n] >= l[:n]) & (yt[:n] <= h[:n])
    return float(inside.mean())


@dataclass
class ConformalCalibrator:
    """Calibración por horizonte. En producción, ACI ajusta el ancho."""

    q_offsets: dict[tuple[int, str], float] = field(default_factory=dict)
    interval_offset: dict[int, float] = field(default_factory=dict)
    aci_gamma: float = 0.02
    aci_alpha: float = 0.10
    aci_state: float = 0.10  # se resta aci_alpha al aplicar; arranque neutro

    def fit(
        self,
        y: np.ndarray,
        q10: np.ndarray,
        q50: np.ndarray,
        q90: np.ndarray,
        q95: np.ndarray,
        *,
        horizon_min: int,
    ) -> None:
        h = int(horizon_min)
        self.q_offsets[(h, "q10")] = split_conformal_offset(y, q10, tau=0.10)
        self.q_offsets[(h, "q50")] = split_conformal_offset(y, q50, tau=0.50)
        self.q_offsets[(h, "q90")] = split_conformal_offset(y, q90, tau=0.90)
        self.q_offsets[(h, "q95")] = split_conformal_offset(y, q95, tau=0.95)
        self.interval_offset[h] = interval_conformal_offset(y, q10, q90, target=0.90)

    def apply(self, pred: pd.DataFrame) -> pd.DataFrame:
        out = pred.copy()
        for h, g in out.groupby("horizon_min"):
            idx = g.index
            off50 = self.q_offsets.get((int(h), "q50"), 0.0)
            off95 = self.q_offsets.get((int(h), "q95"), 0.0)
            extra = self.interval_offset.get(int(h), 0.0) + max(0.0, self.aci_state - self.aci_alpha)
            extra = max(0.0, float(extra))
            # [q10, q90] se calibra como intervalo 90 %; no sumar otra vez los offsets de cola.
            out.loc[idx, "q10"] = g["q10"].to_numpy() - extra
            out.loc[idx, "q50"] = g["q50"].to_numpy() + off50
            out.loc[idx, "q90"] = g["q90"].to_numpy() + extra
            out.loc[idx, "q95"] = np.maximum(g["q95"].to_numpy() + off95, g["q90"].to_numpy() + extra)
        cols = ["q10", "q50", "q90", "q95"]
        arr = np.sort(out[cols].to_numpy(dtype=float), axis=1)
        out[cols] = arr
        return out

    def aci_update(self, y: float, q10: float, q90: float) -> None:
        """Ajuste en línea del nivel según cobertura reciente (ACI)."""
        hit = 1.0 if (q10 <= y <= q90) else 0.0
        err = (1.0 - self.aci_alpha) - hit
        self.aci_state = float(max(0.0, self.aci_state + self.aci_gamma * err))


def confidence_from_width(
    q10: float,
    q90: float,
    *,
    nearest_threshold: float | None,
    last_value: float,
) -> str:
    """alta/media/baja según el ancho relativo al umbral más cercano."""
    width = float(q90) - float(q10)
    if not np.isfinite(width) or width < 0:
        return "baja"
    if nearest_threshold is None or not np.isfinite(nearest_threshold):
        scale = max(abs(float(last_value)), 1e-6)
    else:
        scale = max(abs(float(nearest_threshold) - float(last_value)), 1e-6)
    rel = width / scale
    if rel < 0.35:
        return "alta"
    if rel < 0.80:
        return "media"
    return "baja"
