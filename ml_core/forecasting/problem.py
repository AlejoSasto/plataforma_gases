"""Contrato del problema de pronóstico (Plan 15 F3). Nadie usa constantes sueltas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

DEFAULT_QUANTILES: tuple[float, ...] = (0.1, 0.5, 0.9, 0.95)
DEFAULT_LEVELS: tuple[str, ...] = ("vigilar", "actuar", "evacuar")
DEFAULT_LOOKBACKS: tuple[int, ...] = (30, 60, 120)


@dataclass(frozen=True)
class ProblemSpec:
    lookback: int
    horizons: tuple[int, ...]
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES
    levels: tuple[str, ...] = DEFAULT_LEVELS
    grid_step_minutes: int = 1
    shift_hours: int = 8
    alert_persistence_steps: int = 2

    def __post_init__(self) -> None:
        if self.lookback < 2:
            raise ValueError("lookback debe ser ≥ 2")
        if not self.horizons:
            raise ValueError("horizons no puede estar vacío")
        if any(h < 1 for h in self.horizons):
            raise ValueError("cada horizonte debe ser ≥ 1")
        if any(q <= 0 or q >= 1 for q in self.quantiles):
            raise ValueError("cuantiles en (0, 1)")

    @property
    def k_max(self) -> int:
        return max(self.horizons)

    @property
    def purge_gap_steps(self) -> int:
        return self.lookback + self.k_max

    @classmethod
    def from_g0(
        cls,
        g0: dict,
        *,
        lookback: int = 60,
        grid_step_minutes: int | None = None,
    ) -> "ProblemSpec":
        raw = g0.get("horizons_min") or []
        horizons = tuple(int(h) for h in raw)
        if not horizons:
            raise ValueError("G0 no define horizontes")
        step = grid_step_minutes
        if step is None:
            dt = g0.get("dt_p50_min_priority_max")
            step = max(1, int(round(float(dt)))) if dt else 1
        return cls(lookback=lookback, horizons=horizons, grid_step_minutes=int(step))

    @classmethod
    def from_g0_file(cls, path: Path | str, **kwargs: object) -> "ProblemSpec":
        import json

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        g0 = payload.get("g0", payload)
        return cls.from_g0(g0, **kwargs)  # type: ignore[arg-type]


def pinball_loss(y: float, q_hat: float, tau: float) -> float:
    err = y - q_hat
    return max(tau * err, (tau - 1) * err)
