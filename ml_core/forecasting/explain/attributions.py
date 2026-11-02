"""Atribuciones por familia: VSN, oclusión, importancias tabulares."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from ml_core.forecasting.explain.factors import heuristic_factors


def occlusion_weights(window: np.ndarray, predict_fn: Callable[[np.ndarray], float]) -> np.ndarray:
    """Sensibilidad por tramos: anula tercios de la ventana."""
    y = np.asarray(window, dtype=float)
    n = y.size
    if n < 3:
        return np.ones(max(n, 1), dtype=float) / max(n, 1)
    base = float(predict_fn(y))
    w = np.zeros(n, dtype=float)
    third = max(1, n // 3)
    for start in range(0, n, third):
        sl = slice(start, min(n, start + third))
        masked = y.copy()
        masked[sl] = float(np.mean(y))
        w[sl] = abs(base - float(predict_fn(masked)))
    s = w.sum()
    return w / s if s > 0 else np.ones(n) / n


def shap_like_from_importances(names: list[str], gains: np.ndarray) -> list[dict[str, Any]]:
    g = np.asarray(gains, dtype=float)
    if g.size == 0:
        return []
    order = np.argsort(-np.abs(g))
    out = []
    for i in order[:5]:
        out.append({"feature": names[int(i)], "weight": float(g[int(i)]), "direction": "up" if g[int(i)] >= 0 else "down"})
    return out


def default_factors(window: np.ndarray, **kwargs: Any) -> list[dict[str, Any]]:
    return heuristic_factors(window, **kwargs)
