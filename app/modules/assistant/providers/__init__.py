"""Elección del proveedor según ASSISTANT_PROVIDER."""

from __future__ import annotations

from app.core.config import settings
from app.modules.assistant.providers.base import LLMProvider, ProviderUnavailable
from app.modules.assistant.providers.gemini import GeminiProvider
from app.modules.assistant.providers.ollama import OllamaProvider


def get_provider() -> LLMProvider:
    mode = (settings.assistant_provider or "off").strip().lower()
    if mode == "off":
        raise ProviderUnavailable()
    if mode == "ollama":
        return OllamaProvider()
    if mode == "gemini":
        if not (settings.gemini_api_key or "").strip():
            raise ProviderUnavailable()
        return GeminiProvider()
    raise ProviderUnavailable()
