"""Tiny Time Mixers. Mixer nativo en CPU (~pocos miles de parámetros)."""

from __future__ import annotations

from pathlib import Path

from ml_core.forecasting.adapters._torch_quantile import TorchQuantileAdapter
from ml_core.forecasting.base import Family


class TTMForecaster(TorchQuantileAdapter):
    name = "ttm"
    family: Family = "fundacional"
    net_kind = "mixer"
    backend = "torch-ttm-lite"

    @classmethod
    def load(cls, path: Path) -> "TTMForecaster":
        base = TorchQuantileAdapter.load(path)
        obj = cls()
        obj.__dict__.update(base.__dict__)
        obj.name = cls.name
        obj.family = cls.family
        obj.net_kind = cls.net_kind
        return obj
