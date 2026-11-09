"""Fallo cerrado: si un modelo no está instalado, no se sustituye."""

from __future__ import annotations


class ModelUnavailableError(RuntimeError):
    def __init__(self, model: str, reason: str) -> None:
        self.model = model
        self.reason = reason
        super().__init__(f"{model} no disponible: {reason}")
