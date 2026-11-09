"""Contrato del proveedor de lenguaje."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ProviderResult:
    calls: list[dict[str, Any]] = field(default_factory=list)
    text: str | None = None
    model: str = ""
    tokens: int | None = None


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        pending: list[dict[str, Any]],
        correction: str | None,
    ) -> ProviderResult:
        """Una vuelta: o llamadas a herramientas, o el JSON final."""


class ProviderError(Exception):
    """El proveedor falló o devolvió algo que no se puede usar."""


class ProviderUnavailable(Exception):
    """No hay proveedor configurado o no hay conexión."""
