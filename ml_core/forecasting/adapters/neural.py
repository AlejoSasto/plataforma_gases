"""LSTM, TFT, PatchTST, iTransformer.

Si neuralforecast no está instalado, el adaptador falla.
No se entrena otra red con el nombre del modelo.
"""

from __future__ import annotations

from pathlib import Path

from ml_core.forecasting.base import Family


def _try_neuralforecast() -> bool:
    try:
        import neuralforecast  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _fit_native(self, train, spec) -> None:
    """Exige neuralforecast. Si falta o no entrena, no hay red sustituta."""
    del train, spec
    from ml_core.forecasting.errors import ModelUnavailableError

    if not _try_neuralforecast():
        raise ModelUnavailableError(self.name, "falta neuralforecast")
    raise ModelUnavailableError(
        self.name,
        "neuralforecast está instalado pero no hay un entrenamiento nativo cableado; no se usa otra red",
    )


def _predict_native(self, context, spec):
    del context, spec
    from ml_core.forecasting.errors import ModelUnavailableError

    raise ModelUnavailableError(self.name, "no hay pesos nativos cargados")


class LSTMForecaster:
    name = "lstm"
    family: Family = "recurrente"
    net_kind = "lstm"
    backend = "neuralforecast"
    fit = _fit_native
    predict_quantiles = _predict_native


class TFTForecaster:
    name = "tft"
    family: Family = "transformer"
    net_kind = "tft"
    backend = "neuralforecast"
    fit = _fit_native
    predict_quantiles = _predict_native


class PatchTSTForecaster:
    name = "patchtst"
    family: Family = "transformer"
    net_kind = "patch"
    backend = "neuralforecast"
    fit = _fit_native
    predict_quantiles = _predict_native


class ITransformerForecaster:
    name = "itransformer"
    family: Family = "transformer"
    net_kind = "patch"
    backend = "neuralforecast"
    fit = _fit_native
    predict_quantiles = _predict_native


def load_named(path: Path, cls):
    from ml_core.forecasting.adapters._torch_quantile import TorchQuantileAdapter

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
