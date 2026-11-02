"""LSTM, TFT, PatchTST, iTransformer.

Si neuralforecast está instalado se usa como backend nativo; si no, las
versiones compactas en CPU (`_torch_quantile`) cumplen el contrato.
"""

from __future__ import annotations

from pathlib import Path

from ml_core.forecasting.adapters._torch_quantile import TorchQuantileAdapter
from ml_core.forecasting.base import Family


def _try_neuralforecast() -> bool:
    try:
        import neuralforecast  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


class LSTMForecaster(TorchQuantileAdapter):
    name = "lstm"
    family: Family = "recurrente"
    net_kind = "lstm"
    backend = "torch-lite" if not _try_neuralforecast() else "neuralforecast"


class TFTForecaster(TorchQuantileAdapter):
    name = "tft"
    family: Family = "transformer"
    net_kind = "tft"
    backend = "torch-lite" if not _try_neuralforecast() else "neuralforecast"


class PatchTSTForecaster(TorchQuantileAdapter):
    name = "patchtst"
    family: Family = "transformer"
    net_kind = "patch"
    backend = "torch-lite" if not _try_neuralforecast() else "neuralforecast"


class ITransformerForecaster(TorchQuantileAdapter):
    name = "itransformer"
    family: Family = "transformer"
    net_kind = "patch"
    backend = "torch-lite" if not _try_neuralforecast() else "neuralforecast"


def load_named(path: Path, cls: type[TorchQuantileAdapter]) -> TorchQuantileAdapter:
    obj = TorchQuantileAdapter.load(path)
    out = cls()
    out.__dict__.update(obj.__dict__)
    out.name = cls.name
    out.family = cls.family
    out.net_kind = cls.net_kind
    return out


LSTMForecaster.load = classmethod(lambda cls, path: load_named(path, cls))  # type: ignore[method-assign]
TFTForecaster.load = classmethod(lambda cls, path: load_named(path, cls))  # type: ignore[method-assign]
PatchTSTForecaster.load = classmethod(lambda cls, path: load_named(path, cls))  # type: ignore[method-assign]
ITransformerForecaster.load = classmethod(lambda cls, path: load_named(path, cls))  # type: ignore[method-assign]
