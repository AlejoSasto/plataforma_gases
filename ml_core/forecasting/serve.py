"""Ciclo de inferencia: cuantiles → conformal → decisión → explicación.

Sin modelo en producción solo se emiten avisos confirmados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ml_core.domain.thresholds import ThresholdSpec, levels_for_gas
from ml_core.forecasting.conformal import ConformalCalibrator, confidence_from_width
from ml_core.forecasting.decision import (
    DecisionState,
    confirmed_level,
    operational_level,
    probs_for_horizon,
)
from ml_core.forecasting.explain.factors import heuristic_factors
from ml_core.forecasting.explain.narrator import narrate
from ml_core.forecasting.problem import ProblemSpec


NO_MODEL_MESSAGE = "El sistema está mostrando solo lo que marcan los sensores en este momento."


@dataclass
class InferResult:
    status_level: str
    kind: str  # anticipado | confirmado | ninguno
    exceed_prob: dict[str, Any]
    confidence: str
    quantiles: list[dict[str, Any]]
    plain_text: str
    factors: list[dict[str, Any]]
    confirmed_only: bool


def infer_sensor(
    context: pd.DataFrame,
    spec: ProblemSpec,
    *,
    gas: str = "CH4",
    model=None,
    calibrator: ConformalCalibrator | None = None,
    state: DecisionState | None = None,
    last_value: float | None = None,
) -> InferResult:
    specs = levels_for_gas(gas)
    y = pd.to_numeric(context["y"] if "y" in context.columns else context.iloc[:, 0], errors="coerce").dropna()
    current = float(last_value if last_value is not None else (y.iloc[-1] if len(y) else 0.0))
    confirmed = confirmed_level(current, specs)
    if model is None:
        level = confirmed or "normal"
        return InferResult(
            status_level=level,
            kind="confirmado" if confirmed else "ninguno",
            exceed_prob={},
            confidence="alta" if confirmed else "media",
            quantiles=[],
            plain_text=NO_MODEL_MESSAGE if not confirmed else "El sensor ya superó el límite; hay que actuar ahora.",
            factors=[],
            confirmed_only=True,
        )

    pred = model.predict_quantiles(context, spec)
    if calibrator is not None:
        pred = calibrator.apply(pred)
    qrows = []
    probs_acc: dict[str, list[float]] = {"vigilar": [], "actuar": [], "evacuar": []}
    for _, row in pred.iterrows():
        q = {
            "horizon_min": int(row["horizon_min"]),
            "q10": float(row["q10"]),
            "q50": float(row["q50"]),
            "q90": float(row["q90"]),
            "q95": float(row["q95"]),
        }
        qrows.append(q)
        p = probs_for_horizon(q["q10"], q["q50"], q["q90"], q["q95"], specs)
        for k, v in p.items():
            probs_acc.setdefault(k, []).append(v)
    probs = {k: float(max(vs) if vs else 0.0) for k, vs in probs_acc.items()}
    state = state or DecisionState(persistence_steps=spec.alert_persistence_steps)
    anticipated = state.update(probs)
    status = operational_level(confirmed, anticipated)
    kind = "confirmado" if confirmed else ("anticipado" if anticipated != "normal" else "ninguno")
    q0 = qrows[0] if qrows else {"q10": current, "q90": current, "q50": current}
    nearest = min((abs(current - s.value), s.value) for s in specs)[1] if specs else None
    conf = confidence_from_width(q0["q10"], q0["q90"], nearest_threshold=nearest, last_value=current)
    win = y.to_numpy(dtype=float) if len(y) else np.array([current])
    factors = heuristic_factors(win, gas=gas, specs=specs, step_minutes=spec.grid_step_minutes)
    text = narrate(factors)
    if confirmed:
        text = "El sensor ya superó el límite. " + text
        from ml_core.forecasting.explain.language import assert_plain

        assert_plain(text)
    return InferResult(
        status_level=status,
        kind=kind,
        exceed_prob={lvl: {str(q["horizon_min"]): probs.get(lvl, 0.0) for q in qrows} for lvl in ("vigilar", "actuar", "evacuar")},
        confidence=conf,
        quantiles=qrows,
        plain_text=text,
        factors=factors,
        confirmed_only=False,
    )
